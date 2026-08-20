from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

pytest.importorskip(
    "app.repositories.interview_mapper",
    reason="Fase 3 pendente: app.repositories.interview_mapper",
)

from app.core.domain.interfaces import Evaluation, Question  # noqa: E402
from app.core.llm.interfaces import LLMResponse  # noqa: E402
from app.repositories import interview_mapper  # noqa: E402


def _question(
    id: str = "sqs-01",
    topic: str = "dead_letter_queue",
    difficulty: int = 1,
    prompt: str = "O que é uma DLQ?",
) -> Question:
    return Question(id=id, topic=topic, difficulty=difficulty, prompt=prompt)


def _evaluation(level: str = "strong", feedback: str = "Boa resposta.") -> Evaluation:
    return Evaluation(
        topic="dead_letter_queue",
        level=level,
        feedback=feedback,
        raw_response=LLMResponse(
            text=f"NIVEL: {level.upper()}\nFEEDBACK: {feedback}",
            provider="groq",
            model="llama-test",
            tokens_used=15,
        ),
    )


def _active_interview_row(current: Question) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        domain="async_messaging",
        status="active",
        topic=current.topic,
        difficulty=current.difficulty,
        current_question_id=current.id,
        current_question_topic=current.topic,
        current_question_difficulty=current.difficulty,
        current_question_prompt=current.prompt,
        questions_answered=0,
        finished_at=None,
    )


def _turn_row(
    turn_number: int,
    question: Question,
    answer: str,
    evaluation: Evaluation,
) -> SimpleNamespace:
    return SimpleNamespace(
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
        evaluation_raw_response=interview_mapper.evaluation_to_jsonb(evaluation),
        created_at=datetime.now(UTC),
    )


def test_to_state_active_interview_restores_current_question():
    current = _question()
    interview = _active_interview_row(current)

    state = interview_mapper.to_state(interview, turns=[])

    assert state.finished is False
    assert state.current_question == current
    assert state.history == []


def test_to_state_after_n_turns_preserves_history_length_and_order():
    q1 = _question(id="sqs-01")
    q2 = _question(id="sqs-05", difficulty=2, prompt="Como configurar redrive?")
    ev1 = _evaluation(level="medium", feedback="Parcial.")
    ev2 = _evaluation(level="strong", feedback="Completa.")
    interview = _active_interview_row(q2)
    interview.questions_answered = 2
    turns = [
        _turn_row(0, q1, "resposta 1", ev1),
        _turn_row(1, q2, "resposta 2", ev2),
    ]

    state = interview_mapper.to_state(interview, turns=turns)

    assert len(state.history) == 2
    assert state.history[0][0].id == "sqs-01"
    assert state.history[1][0].id == "sqs-05"
    assert state.history[0][1].level == "medium"
    assert state.history[1][1].feedback == "Completa."


def test_finished_state_api_mapping_omits_current_question():
    q1 = _question()
    ev1 = _evaluation()
    interview = SimpleNamespace(
        id=uuid4(),
        domain="async_messaging",
        status="finished",
        topic=q1.topic,
        difficulty=q1.difficulty,
        current_question_id=None,
        current_question_topic=None,
        current_question_difficulty=None,
        current_question_prompt=None,
        questions_answered=1,
        finished_at=datetime.now(UTC),
    )
    turns = [_turn_row(0, q1, "resposta", ev1)]

    state = interview_mapper.to_state(interview, turns=turns)
    response = interview_mapper.to_interview_response(interview, state)

    assert state.finished is True
    assert response["finished"] is True
    assert "current_question" not in response


def test_evaluation_raw_response_jsonb_round_trip():
    evaluation = _evaluation()
    payload = interview_mapper.evaluation_to_jsonb(evaluation)

    restored = interview_mapper.evaluation_from_jsonb(payload)

    assert restored.provider == evaluation.raw_response.provider
    assert restored.model == evaluation.raw_response.model
    assert restored.text == evaluation.raw_response.text
    assert restored.tokens_used == evaluation.raw_response.tokens_used
