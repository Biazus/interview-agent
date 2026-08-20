from app.agents.reporting_schema import ReportLLMOutput


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
