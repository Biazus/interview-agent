import pytest

from sqlalchemy.exc import IntegrityError

from app.repositories.interview_repository import InterviewRepository


@pytest.fixture
async def repository(interview_repository_with_candidate) -> InterviewRepository:
    repository, _ = interview_repository_with_candidate
    return repository


@pytest.fixture
def candidate_id(interview_repository_with_candidate):
    _, candidate_id = interview_repository_with_candidate
    return candidate_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_second_active_interview_raises_integrity_error(
    repository, candidate_id, require_postgres
):
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
async def test_duplicate_turn_number_raises_integrity_error(
    repository, candidate_id, require_postgres
):
    # Requer migration level→score (coluna evaluation_score).
    # Falha até o executor aplicar a migration e atualizar InterviewRepository.
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
        "evaluation_score": 55,
        "evaluation_feedback": "ok",
        "evaluation_provider": "fake",
        "evaluation_model": "test",
        "evaluation_raw_response": {"text": '{"score": 55, "feedback": "ok"}'},
    }

    await repository.add_turn(interview_id=interview_id, turn_number=0, **turn_payload)

    with pytest.raises(IntegrityError):
        await repository.add_turn(
            interview_id=interview_id, turn_number=0, **turn_payload
        )
