from dataclasses import dataclass

from app.core.domain.interfaces import Evaluation, InterviewState, Question, CandidateReport
from app.core.llm.interfaces import LLMProvider

_SYSTEM_PROMPT = """Você é um Relator de entrevistas técnicas. Sua tarefa é compilar
o histórico de perguntas e avaliações de um candidato em um relatório final,
humanizado, destacando pontos fortes, pontos fracos e sugestões de estudo
para futuras entrevistas.

Responda EXATAMENTE no formato abaixo, sem texto fora dele:

RESUMO: <um parágrafo corrido resumindo o desempenho geral do candidato>
PONTOS_FORTES: <item 1> | <item 2> | <item 3>
PONTOS_FRACOS: <item 1> | <item 2> | <item 3>
SUGESTOES: <item 1> | <item 2> | <item 3>
"""


class ReportingAgent:
    """Compila o histórico de uma InterviewState em um relatório final,
    usando o LLM para sintetizar pontos fortes, fracos e sugestões a partir
    dos feedbacks já gerados pelo Avaliador ao longo da entrevista."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def generate_report(self, state: InterviewState) -> CandidateReport:
        transcript = self._build_transcript(state.history)
        prompt = f"{_SYSTEM_PROMPT}\n\nHistórico da entrevista:\n{transcript}"

        response = await self._llm.generate(prompt)
        print("--- RAW LLM RESPONSE ---")
        print(repr(response.text))
        print("--- END RAW ---")
        return self._parse_response(response.text, total_questions=len(state.history))

    def _build_transcript(self, history: list[tuple[Question, Evaluation]]) -> str:
        lines = []
        for i, (question, evaluation) in enumerate(history, start=1):
            lines.append(
                f"{i}. [{question.topic}] Pergunta: {question.prompt}\n"
                f"   Nível: {evaluation.level} | Feedback: {evaluation.feedback}"
            )
        return "\n".join(lines)

    def _parse_response(self, text: str, total_questions: int) -> CandidateReport:
        fields: dict[str, str] = {}
        for line in text.strip().splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip().upper()] = value.strip()

        return CandidateReport(
            overall_summary=fields.get("RESUMO", ""),
            strengths=self._split_items(fields.get("PONTOS_FORTES", "")),
            weaknesses=self._split_items(fields.get("PONTOS_FRACOS", "")),
            suggestions=self._split_items(fields.get("SUGESTOES", "")),
            total_questions=total_questions,
        )

    def _split_items(self, raw: str) -> list[str]:
        return [item.strip() for item in raw.split("|") if item.strip()]