from collections.abc import Callable
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluator import EvaluationParseError
from app.agents.orchestrator import OrchestratorAgent
from app.api.errors import APIError
from app.core.domain.interfaces import CandidateReport
from app.core.domain.registry import (
    DomainEnum,
    DomainNotRegisteredError,
    get_cached_domain,
)
from app.core.llm.exceptions import LLMProviderError
from app.repositories.interview_mapper import to_interview_response, to_report_response
from app.repositories.interview_repository import InterviewRepository


class InterviewService:
    def __init__(
        self,
        repository: InterviewRepository,
        session: AsyncSession,
        orchestrator_factory: Callable[[DomainEnum], OrchestratorAgent],
    ) -> None:
        self._repository = repository
        self._session = session
        self._orchestrator_factory = orchestrator_factory

    async def start_interview(
        self,
        candidate_id: UUID,
        domain: str,
        topic: str,
        difficulty: int = 1,
    ) -> dict:
        active = await self._repository.get_active_by_candidate(candidate_id)
        if active is not None:
            raise APIError(
                status_code=409,
                detail="Já existe uma entrevista ativa para este candidato.",
                code="ACTIVE_INTERVIEW_EXISTS",
            )

        domain_enum = self._parse_domain(domain)
        module = self._resolve_domain_module(domain_enum)

        if topic not in module.question_bank.topics():
            raise APIError(
                status_code=400,
                detail="Tópico inválido para o domínio informado.",
                code="INVALID_TOPIC",
            )

        orchestrator = self._orchestrator_factory(domain_enum)
        state = orchestrator.start(topic, difficulty)
        question = state.current_question

        try:
            interview_id = await self._repository.create_interview(
                candidate_id=candidate_id,
                domain=domain_enum.value,
                topic=state.topic,
                difficulty=state.difficulty,
                current_question_id=question.id,
                current_question_topic=question.topic,
                current_question_difficulty=question.difficulty,
                current_question_prompt=question.prompt,
            )
        except IntegrityError as exc:
            await self._session.rollback()
            raise APIError(
                status_code=409,
                detail="Já existe uma entrevista ativa para este candidato.",
                code="ACTIVE_INTERVIEW_EXISTS",
            ) from exc

        interview = await self._repository.get_by_id_for_candidate(
            interview_id, candidate_id
        )
        if interview is None:
            raise APIError(
                status_code=404,
                detail="Entrevista não encontrada.",
                code="INTERVIEW_NOT_FOUND",
            )

        return to_interview_response(interview, state)

    async def get_active_interview(self, candidate_id: UUID) -> dict:
        interview = await self._repository.get_active_by_candidate(candidate_id)
        if interview is None:
            raise APIError(
                status_code=404,
                detail="Nenhuma entrevista ativa encontrada.",
                code="NO_ACTIVE_INTERVIEW",
            )

        turns = await self._repository.get_turns(interview.id)
        from app.repositories import interview_mapper

        state = interview_mapper.to_state(interview, turns)
        return to_interview_response(interview, state)

    async def submit_answer(
        self,
        candidate_id: UUID,
        interview_id: UUID,
        answer: str,
    ) -> dict:
        if not answer.strip():
            raise APIError(
                status_code=422,
                detail="A resposta não pode ser vazia.",
                code="EMPTY_ANSWER",
            )

        interview = await self._repository.get_by_id_for_candidate(
            interview_id, candidate_id
        )
        if interview is None:
            raise APIError(
                status_code=404,
                detail="Entrevista não encontrada.",
                code="INTERVIEW_NOT_FOUND",
            )

        if interview.status == "finished":
            raise APIError(
                status_code=409,
                detail="A entrevista já foi finalizada.",
                code="INTERVIEW_ALREADY_FINISHED",
            )

        turns = await self._repository.get_turns(interview_id)
        from app.repositories import interview_mapper

        state = interview_mapper.to_state(interview, turns)
        orchestrator = self._orchestrator_factory(DomainEnum(interview.domain))

        try:
            new_state = await orchestrator.submit_answer(state, answer)
        except (LLMProviderError, EvaluationParseError) as exc:
            raise APIError(
                status_code=503,
                detail="Serviço de avaliação temporariamente indisponível.",
                code="LLM_UNAVAILABLE",
            ) from exc

        report_to_persist: CandidateReport | None = None
        if new_state.finished:
            try:
                report_to_persist = await orchestrator.get_report(new_state)
            except LLMProviderError:
                report_to_persist = None

        answered_question, evaluation = new_state.history[-1]

        try:
            await self._repository.save_turn_and_update_interview(
                interview_id=interview_id,
                question=answered_question,
                answer=answer,
                evaluation=evaluation,
                new_state=new_state,
            )
            if report_to_persist is not None:
                await self._repository.save_report(interview_id, report_to_persist)
        except IntegrityError as exc:
            await self._session.rollback()
            raise APIError(
                status_code=409,
                detail="Turno duplicado para esta entrevista.",
                code="DUPLICATE_TURN",
            ) from exc

        updated = await self._repository.get_by_id_for_candidate(
            interview_id, candidate_id
        )
        if updated is None:
            raise APIError(
                status_code=404,
                detail="Entrevista não encontrada.",
                code="INTERVIEW_NOT_FOUND",
            )

        return to_interview_response(updated, new_state)

    async def get_report(self, candidate_id: UUID, interview_id: UUID) -> dict:
        interview = await self._repository.get_by_id_for_candidate(
            interview_id, candidate_id
        )
        if interview is None:
            raise APIError(
                status_code=404,
                detail="Entrevista não encontrada.",
                code="INTERVIEW_NOT_FOUND",
            )

        if interview.status != "finished":
            raise APIError(
                status_code=409,
                detail="A entrevista ainda está em andamento.",
                code="INTERVIEW_NOT_FINISHED",
            )

        existing = await self._repository.get_report(interview_id)
        if existing is not None:
            from app.repositories import interview_mapper

            report = interview_mapper.report_from_row(existing)
            return to_report_response(interview_id, report)

        turns = await self._repository.get_turns(interview_id)
        from app.repositories import interview_mapper

        state = interview_mapper.to_state(interview, turns)
        orchestrator = self._orchestrator_factory(DomainEnum(interview.domain))

        try:
            report = await orchestrator.get_report(state)
        except LLMProviderError as exc:
            raise APIError(
                status_code=503,
                detail="Serviço de avaliação temporariamente indisponível.",
                code="LLM_UNAVAILABLE",
            ) from exc

        await self._repository.save_report(interview_id, report)
        return to_report_response(interview_id, report)

    def _parse_domain(self, domain: str) -> DomainEnum:
        try:
            return DomainEnum(domain)
        except ValueError as exc:
            raise APIError(
                status_code=400,
                detail="Domínio inválido.",
                code="INVALID_DOMAIN",
            ) from exc

    def _resolve_domain_module(self, domain_enum: DomainEnum):
        try:
            return get_cached_domain(domain_enum)
        except DomainNotRegisteredError as exc:
            raise APIError(
                status_code=400,
                detail="Domínio não registrado.",
                code="INVALID_DOMAIN",
            ) from exc
