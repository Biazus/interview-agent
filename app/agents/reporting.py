from app.agents.reporting_schema import ReportLLMOutput
from app.core.domain.interfaces import (
    CandidateReport,
    Evaluation,
    InterviewState,
    Question,
)
from app.core.llm.interfaces import LLMProvider
from app.core.llm.structured import generate_structured

_SYSTEM_PROMPT = """Você é um Relator de entrevistas técnicas. Compila o histórico em um
relatório final, humanizado, com pontos fortes, fracos e sugestões de estudo.

Responda SOMENTE com um objeto JSON válido, sem markdown nem texto fora do JSON.
Use exatamente estas chaves em português:

- "resumo": string com até 2 frases curtas sobre o desempenho geral
- "pontos_fortes": array de strings (até 3 itens curtos)
- "pontos_fracos": array de strings (até 3 itens curtos)
- "sugestoes": array de strings (até 3 itens curtos)
"""


class ReportingAgent:
    """Compila o histórico de uma InterviewState em um relatório final,
    usando o LLM para sintetizar pontos fortes, fracos e sugestões a partir
    dos feedbacks já gerados pelo Avaliador ao longo da entrevista."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def generate_report(self, state: InterviewState) -> CandidateReport:
        transcript = self._build_transcript(state.history)
        prompt = f"Histórico da entrevista:\n{transcript}"

        output = await generate_structured(
            self._llm,
            prompt,
            ReportLLMOutput,
            system_prompt=_SYSTEM_PROMPT,
        )
        return output.to_candidate_report(total_questions=len(state.history))

    def _build_transcript(self, history: list[tuple[Question, Evaluation]]) -> str:
        lines = []
        for i, (question, evaluation) in enumerate(history, start=1):
            lines.append(
                f"{i}. [{question.topic}] nível={evaluation.level} | "
                f"feedback: {evaluation.feedback}"
            )
        return "\n".join(lines)
