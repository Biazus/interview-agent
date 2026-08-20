from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.models import Interview, InterviewReport, InterviewTurn
from app.core.domain.interfaces import (
    CandidateReport,
    Evaluation,
    InterviewState,
    Question,
)
from app.repositories.interview_mapper import evaluation_to_jsonb


def _build_turn(
    interview_id: UUID,
    turn_number: int,
    question: Question,
    answer: str,
    evaluation: Evaluation,
) -> InterviewTurn:
    return InterviewTurn(
        interview_id=interview_id,
        turn_number=turn_number,
        question_id=question.id,
        question_topic=question.topic,
        question_difficulty=question.difficulty,
        question_prompt=question.prompt,
        answer_text=answer,
        evaluation_level=evaluation.level,
        evaluation_feedback=evaluation.feedback,
        evaluation_provider=evaluation.raw_response.provider,
        evaluation_model=evaluation.raw_response.model,
        evaluation_raw_response=evaluation_to_jsonb(evaluation),
    )


def _apply_state_to_interview(interview: Interview, state: InterviewState) -> None:
    interview.questions_answered = len(state.history)
    interview.topic = state.topic
    interview.difficulty = state.difficulty

    if state.finished:
        interview.status = "finished"
        interview.current_question_id = None
        interview.current_question_topic = None
        interview.current_question_difficulty = None
        interview.current_question_prompt = None
        if interview.finished_at is None:
            interview.finished_at = datetime.now(UTC)
        return

    current = state.current_question
    interview.current_question_id = current.id
    interview.current_question_topic = current.topic
    interview.current_question_difficulty = current.difficulty
    interview.current_question_prompt = current.prompt


class InterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_interview(
        self,
        candidate_id: UUID,
        domain: str,
        topic: str,
        difficulty: int,
        current_question_id: str,
        current_question_topic: str,
        current_question_difficulty: int,
        current_question_prompt: str,
    ) -> UUID:
        interview = Interview(
            candidate_id=candidate_id,
            domain=domain,
            status="active",
            topic=topic,
            difficulty=difficulty,
            current_question_id=current_question_id,
            current_question_topic=current_question_topic,
            current_question_difficulty=current_question_difficulty,
            current_question_prompt=current_question_prompt,
            questions_answered=0,
        )
        self._session.add(interview)
        await self._session.flush()
        return interview.id

    async def get_active_by_candidate(self, candidate_id: UUID) -> Interview | None:
        result = await self._session.execute(
            select(Interview).where(
                Interview.candidate_id == candidate_id,
                Interview.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_candidate(
        self, interview_id: UUID, candidate_id: UUID
    ) -> Interview | None:
        result = await self._session.execute(
            select(Interview).where(
                Interview.id == interview_id,
                Interview.candidate_id == candidate_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_turns(self, interview_id: UUID) -> list[InterviewTurn]:
        result = await self._session.execute(
            select(InterviewTurn)
            .where(InterviewTurn.interview_id == interview_id)
            .order_by(InterviewTurn.turn_number)
        )
        return list(result.scalars().all())

    async def get_report(self, interview_id: UUID) -> InterviewReport | None:
        result = await self._session.execute(
            select(InterviewReport).where(InterviewReport.interview_id == interview_id)
        )
        return result.scalar_one_or_none()

    async def add_turn(
        self, interview_id: UUID, turn_number: int, **payload: object
    ) -> None:
        turn = InterviewTurn(
            interview_id=interview_id,
            turn_number=turn_number,
            question_id=str(payload["question_id"]),
            question_topic=str(payload["question_topic"]),
            question_difficulty=int(payload["question_difficulty"]),
            question_prompt=str(payload["question_prompt"]),
            answer_text=str(payload["answer_text"]),
            evaluation_level=str(payload["evaluation_level"]),
            evaluation_feedback=str(payload["evaluation_feedback"]),
            evaluation_provider=str(payload["evaluation_provider"]),
            evaluation_model=str(payload["evaluation_model"]),
            evaluation_raw_response=dict(payload["evaluation_raw_response"]),
        )
        self._session.add(turn)
        await self._session.flush()

    async def save_turn_and_update_interview(
        self,
        interview_id: UUID,
        question: Question,
        answer: str,
        evaluation: Evaluation,
        new_state: InterviewState,
    ) -> None:
        turn_number = len(new_state.history) - 1
        self._session.add(
            _build_turn(interview_id, turn_number, question, answer, evaluation)
        )

        interview = await self._session.get(Interview, interview_id)
        if interview is None:
            raise ValueError(f"Interview {interview_id} not found")

        _apply_state_to_interview(interview, new_state)
        await self._session.flush()

    async def save_report(self, interview_id: UUID, report: CandidateReport) -> None:
        row = InterviewReport(
            interview_id=interview_id,
            overall_summary=report.overall_summary,
            strengths=list(report.strengths),
            weaknesses=list(report.weaknesses),
            suggestions=list(report.suggestions),
            total_questions=report.total_questions,
        )
        self._session.add(row)
        await self._session.flush()
