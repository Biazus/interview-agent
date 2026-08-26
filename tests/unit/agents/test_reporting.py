from unittest.mock import MagicMock

from app.agents.reporting_schema import ReportLLMOutput
from app.agents.reporting import ReportingAgent
from app.core.domain.interfaces import Evaluation, InterviewState, Question
from app.core.llm.interfaces import LLMResponse


def test_report_llm_output_maps_to_candidate_report():
    output = ReportLLMOutput(
        resumo="Desempenho fraco em DLQ.",
        pontos_fortes=["Conhece o conceito"],
        pontos_fracos=["Respostas vagas"],
        sugestoes=["Estudar SQS"],
    )
    report = output.to_candidate_report(total_questions=5)

    assert report.overall_summary == "Desempenho fraco em DLQ."
    assert report.strengths == ["Conhece o conceito"]
    assert report.weaknesses == ["Respostas vagas"]
    assert report.suggestions == ["Estudar SQS"]
    assert report.total_questions == 5


def test_report_llm_output_normalizes_empty_lists():
    output = ReportLLMOutput.model_validate(
        {
            "resumo": "Ok",
            "pontos_fortes": [],
            "pontos_fracos": ["x"],
            "sugestoes": ["y"],
        }
    )

    assert len(output.pontos_fortes) == 1
    assert "Nenhum ponto forte" in output.pontos_fortes[0]
    assert output.pontos_fracos == ["x"]
    assert output.sugestoes == ["y"]


def test_build_transcript_uses_score_not_level():
    agent = ReportingAgent(llm=MagicMock())  # type: ignore[arg-type]
    question = Question(
        id="sqs-01",
        topic="dead_letter_queue",
        difficulty=1,
        prompt="O que é uma DLQ?",
    )
    evaluation = Evaluation(
        topic="dead_letter_queue",
        score=85,
        feedback="Resposta completa.",
        raw_response=LLMResponse(text="", provider="test", model="test"),
    )
    state = InterviewState(
        topic="dead_letter_queue",
        difficulty=1,
        current_question=question,
        history=[(question, evaluation)],
    )

    transcript = agent._build_transcript(state.history)

    assert "nota=85" in transcript
    assert "nível=" not in transcript
    assert "level=" not in transcript
