import os
from uuid import uuid4

import pytest

pytest.importorskip(
    "app.repositories.interview_repository",
    reason="Fase 3 pendente: app.repositories.interview_repository",
)

from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.repositories.interview_repository import InterviewRepository  # noqa: E402


def _postgres_available() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return url.startswith("postgresql")


@pytest.fixture
async def repository():
    from app.core.db.session import async_session_factory

    async with async_session_factory() as session:
        yield InterviewRepository(session)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_second_active_interview_raises_integrity_error(repository):
    if not _postgres_available():
        pytest.skip("DATABASE_URL Postgres não configurada")

    candidate_id = uuid4()

    await repository.create_interview(
        candidate_id=candidate_id,
        domain="async_messaging",
        topic="dead_letter_queue",
        difficulty=1,
        current_question_id="sqs-01",
        current_question_topic="dead_letter_queue",
        current_question_difficulty=1,
        current_question_prompt="O que é uma DLQ?",
    )

    with pytest.raises(IntegrityError):
        await repository.create_interview(
            candidate_id=candidate_id,
            domain="async_messaging",
            topic="batch_processing",
            difficulty=1,
            current_question_id="lambda-10",
            current_question_topic="batch_processing",
            current_question_difficulty=1,
            current_question_prompt="Como funciona batch?",
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_turn_number_raises_integrity_error(repository):
    if not _postgres_available():
        pytest.skip("DATABASE_URL Postgres não configurada")

    candidate_id = uuid4()
    interview_id = await repository.create_interview(
        candidate_id=candidate_id,
        domain="async_messaging",
        topic="dead_letter_queue",
        difficulty=1,
        current_question_id="sqs-01",
        current_question_topic="dead_letter_queue",
        current_question_difficulty=1,
        current_question_prompt="O que é uma DLQ?",
    )

    turn_payload = {
        "question_id": "sqs-01",
        "question_topic": "dead_letter_queue",
        "question_difficulty": 1,
        "question_prompt": "O que é uma DLQ?",
        "answer_text": "resposta",
        "evaluation_level": "medium",
        "evaluation_feedback": "ok",
        "evaluation_provider": "fake",
        "evaluation_model": "test",
        "evaluation_raw_response": {"text": "NIVEL: MEDIA"},
    }

    await repository.add_turn(interview_id=interview_id, turn_number=0, **turn_payload)

    with pytest.raises(IntegrityError):
        await repository.add_turn(
            interview_id=interview_id, turn_number=0, **turn_payload
        )
