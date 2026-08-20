from app.agents.reporting_schema import ReportLLMOutput
from app.core.llm.interfaces import LLMResponse
from app.core.llm.requests import GenerateRequest


class DeterministicLLM:
    """LLM fake com respostas fixas para evaluate e report."""

    def __init__(
        self,
        evaluation_text: str = "NIVEL: FORTE\nFEEDBACK: Boa resposta estruturada.",
        report: ReportLLMOutput | None = None,
    ) -> None:
        self._evaluation_text = evaluation_text
        self._report = report or ReportLLMOutput(
            resumo="Desempenho sólido no tópico.",
            pontos_fortes=["Boa clareza"],
            pontos_fracos=["Pouca profundidade"],
            sugestoes=["Estudar padrões avançados"],
        )
        self.generate_calls: list[GenerateRequest] = []

    async def generate(self, request: GenerateRequest) -> LLMResponse:
        self.generate_calls.append(request)
        if "Relator de entrevistas" in (request.system_prompt or ""):
            return LLMResponse(
                text=self._report.model_dump_json(),
                provider="fake",
                model="deterministic-report",
            )
        return LLMResponse(
            text=self._evaluation_text,
            provider="fake",
            model="deterministic-eval",
        )


class FailingEvaluationLLM(DeterministicLLM):
    """Retorna texto sem NIVEL válido — para testar EvaluationParseError."""

    def __init__(self) -> None:
        super().__init__(evaluation_text="Resposta sem formato esperado.")
