import importlib
import logging
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluator import EvaluationParseError
from app.agents.orchestrator import OrchestratorAgent
from app.core.domain.interfaces import CandidateReport
from app.core.domain.registry import (
    DomainEnum,
    DomainNotRegisteredError,
    get_cached_domain,
)
from app.core.exceptions import (
    ActiveInterviewExists,
    DuplicateTurn,
    EmptyAnswer,
    InterviewAlreadyFinished,
    InterviewNotFinished,
    InterviewNotFound,
    InvalidDomain,
    InvalidTopic,
    LLMUnavailable,
    NoActiveInterview,
)
from app.core.llm.exceptions import LLMProviderError
from app.core.logging import error_type, interview_extra
from app.repositories.interview_mapper import (
    report_from_row,
    to_interview_response,
    to_report_response,
    to_state,
)
from app.repositories.interview_repository import InterviewRepository

logger = logging.getLogger(__name__)

_ACTIVE_INTERVIEW_CONSTRAINT = "uq_interviews_candidate_active"
_DUPLICATE_TURN_CONSTRAINT = "uq_interview_turn_number"


def _integrity_constraint_name(exc: IntegrityError) -> str | None:
    orig = exc.orig
    if orig is None:
        return None
    diag = getattr(orig, "diag", None)
    if diag is not None:
        return getattr(diag, "constraint_name", None)
    return None


def _default_rag_readiness_check(
    collection_name: str, manifest_files: tuple[str, ...]
) -> None:
    from app.core.rag.rag_readiness import check_rag_ready

    check_rag_ready(collection_name, manifest_files)


class InterviewService:
    def __init__(
        self,
        repository: InterviewRepository,
        session: AsyncSession,
        orchestrator_factory: Callable[[DomainEnum], OrchestratorAgent],
        rag_readiness_check: Callable[[str, tuple[str, ...]], None] | None = None,
    ) -> None:
        self._repository = repository
        self._session = session
        self._orchestrator_factory = orchestrator_factory
        self._rag_readiness_check = rag_readiness_check or _default_rag_readiness_check

    async def start_interview(
        self,
        candidate_id: UUID,
        domain: str,
        topic: str,
        difficulty: int = 1,
    ) -> dict:
        active = await self._repository.get_active_by_candidate(candidate_id)
        if active is not None:
            logger.warning(
                "Cannot start interview: candidate already has active interview",
                extra={
                    "candidate_id": str(candidate_id),
                    "reason": "active_interview_exists",
                },
            )
            raise ActiveInterviewExists()

        domain_enum = self._parse_domain(domain)
        module = self._resolve_domain_module(domain_enum)

        if topic not in module.question_bank.topics():
            raise InvalidTopic()

        rag_config = importlib.import_module(
            f"app.domains.{domain_enum.value}.rag_config"
        )
        self._rag_readiness_check(
            rag_config.COLLECTION_NAME, rag_config.SEED_MANIFEST_FILES
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
            if _integrity_constraint_name(exc) == _ACTIVE_INTERVIEW_CONSTRAINT:
                logger.warning(
                    "Cannot start interview: active interview race detected",
                    extra={
                        "candidate_id": str(candidate_id),
                        "reason": "active_interview_exists",
                    },
                )
                raise ActiveInterviewExists() from exc
            logger.error(
                "Unexpected integrity error while creating interview",
                extra={
                    "candidate_id": str(candidate_id),
                    "error_type": error_type(exc),
                },
                exc_info=True,
            )
            raise

        interview = await self._repository.get_by_id_for_candidate(
            interview_id, candidate_id
        )
        if interview is None:
            raise InterviewNotFound()

        rehydrated_state = to_state(interview, [])
        logger.info(
            "Interview started",
            extra={
                "interview_id": str(interview_id),
                "candidate_id": str(candidate_id),
                "domain": domain_enum.value,
                "topic": state.topic,
                "difficulty": state.difficulty,
            },
        )
        return to_interview_response(interview, rehydrated_state)

    async def get_active_interview(self, candidate_id: UUID) -> dict:
        interview = await self._repository.get_active_by_candidate(candidate_id)
        if interview is None:
            raise NoActiveInterview()

        turns = await self._repository.get_turns(interview.id)
        state = to_state(interview, turns)
        return to_interview_response(interview, state)

    async def submit_answer(
        self,
        candidate_id: UUID,
        interview_id: UUID,
        answer: str,
    ) -> dict:
        if not answer.strip():
            raise EmptyAnswer()

        interview = await self._repository.get_by_id_for_candidate(
            interview_id, candidate_id
        )
        if interview is None:
            raise InterviewNotFound()

        if interview.status == "finished":
            raise InterviewAlreadyFinished()

        turns = await self._repository.get_turns(interview_id)
        state = to_state(interview, turns)
        orchestrator = self._orchestrator_factory(DomainEnum(interview.domain))

        try:
            new_state = await orchestrator.submit_answer(state, answer)
        except (LLMProviderError, EvaluationParseError) as exc:
            logger.error(
                "LLM unavailable during answer submission",
                extra=interview_extra(
                    interview_id,
                    candidate_id,
                    error_type=error_type(exc),
                ),
            )
            raise LLMUnavailable() from exc

        report_to_persist: CandidateReport | None = None
        if new_state.finished:
            try:
                report_to_persist = await orchestrator.get_report(new_state)
            except LLMProviderError as exc:
                logger.error(
                    "Failed to generate report on final turn; interview finishes without report",
                    extra=interview_extra(
                        interview_id,
                        candidate_id,
                        error_type=error_type(exc),
                    ),
                )
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
        except IntegrityError as exc:
            await self._session.rollback()
            if _integrity_constraint_name(exc) == _DUPLICATE_TURN_CONSTRAINT:
                logger.warning(
                    "Duplicate turn submission detected",
                    extra=interview_extra(
                        interview_id,
                        candidate_id,
                        reason="duplicate_turn",
                    ),
                )
                raise DuplicateTurn() from exc
            raise

        if report_to_persist is not None:
            try:
                async with self._session.begin_nested():
                    await self._repository.save_report(interview_id, report_to_persist)
            except IntegrityError:
                logger.warning(
                    "Report already saved during concurrent submission",
                    extra=interview_extra(
                        interview_id,
                        candidate_id,
                        reason="report_integrity_race",
                    ),
                )

        updated = await self._repository.get_by_id_for_candidate(
            interview_id, candidate_id
        )
        if updated is None:
            raise InterviewNotFound()

        logger.info(
            "Answer turn saved",
            extra=interview_extra(
                interview_id,
                candidate_id,
                turn_number=len(new_state.history),
                finished=new_state.finished,
                evaluation_level=evaluation.level,
                topic=evaluation.topic,
            ),
        )

        return to_interview_response(updated, new_state)

    async def get_report(self, candidate_id: UUID, interview_id: UUID) -> dict:
        interview = await self._repository.get_by_id_for_candidate(
            interview_id, candidate_id
        )
        if interview is None:
            raise InterviewNotFound()

        if interview.status != "finished":
            raise InterviewNotFinished()

        existing = await self._repository.get_report(interview_id)
        if existing is not None:
            logger.info(
                "Report cache hit",
                extra=interview_extra(interview_id, candidate_id),
            )
            report = report_from_row(existing)
            return to_report_response(interview_id, report)

        turns = await self._repository.get_turns(interview_id)
        state = to_state(interview, turns)
        orchestrator = self._orchestrator_factory(DomainEnum(interview.domain))

        try:
            report = await orchestrator.get_report(state)
        except LLMProviderError as exc:
            logger.error(
                "Failed to generate report",
                extra=interview_extra(
                    interview_id,
                    candidate_id,
                    error_type=error_type(exc),
                ),
            )
            raise LLMUnavailable() from exc

        try:
            await self._repository.save_report(interview_id, report)
        except IntegrityError:
            await self._session.rollback()
            existing = await self._repository.get_report(interview_id)
            if existing is not None:
                logger.warning(
                    "Report save race recovered from existing report",
                    extra=interview_extra(
                        interview_id,
                        candidate_id,
                        reason="report_integrity_race",
                    ),
                )
                report = report_from_row(existing)
                return to_report_response(interview_id, report)
            raise

        logger.info(
            "Report generated successfully",
            extra=interview_extra(interview_id, candidate_id),
        )
        return to_report_response(interview_id, report)

    def _parse_domain(self, domain: str) -> DomainEnum:
        try:
            return DomainEnum(domain)
        except ValueError as exc:
            raise InvalidDomain() from exc

    def _resolve_domain_module(self, domain_enum: DomainEnum):
        try:
            return get_cached_domain(domain_enum)
        except DomainNotRegisteredError as exc:
            raise InvalidDomain("Domínio não registrado.") from exc
