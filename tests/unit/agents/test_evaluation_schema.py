import pytest
from pydantic import ValidationError

from app.agents.evaluation_schema import EvaluationLLMOutput
from app.core.domain.interfaces import Evaluation
from app.core.llm.interfaces import LLMResponse


def test_evaluation_llm_output_accepts_score_in_valid_range():
    output = EvaluationLLMOutput(score=85, feedback="Boa resposta estruturada.")
    assert output.score == 85
    assert output.feedback == "Boa resposta estruturada."


@pytest.mark.parametrize("invalid_score", [0, 101, -1, 1000])
def test_evaluation_llm_output_rejects_out_of_range_score(invalid_score: int):
    with pytest.raises(ValidationError):
        EvaluationLLMOutput(score=invalid_score, feedback="feedback válido")


def test_evaluation_llm_output_rejects_empty_feedback():
    with pytest.raises(ValidationError):
        EvaluationLLMOutput(score=50, feedback="")


def test_to_evaluation_returns_evaluation_with_score():
    raw = LLMResponse(
        text='{"score": 85, "feedback": "Boa resposta."}',
        provider="groq",
        model="llama-test",
        tokens_used=42,
    )
    output = EvaluationLLMOutput(score=85, feedback="Boa resposta.")

    evaluation = output.to_evaluation(topic="dead_letter_queue", raw_response=raw)

    assert isinstance(evaluation, Evaluation)
    assert evaluation.topic == "dead_letter_queue"
    assert evaluation.score == 85
    assert evaluation.feedback == "Boa resposta."
    assert evaluation.raw_response == raw
