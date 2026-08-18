from pydantic import BaseModel, Field

from app.core.domain.interfaces import CandidateReport


class ReportLLMOutput(BaseModel):
    """Schema JSON esperado do Relator."""

    resumo: str = Field(min_length=1, description="Até 2 frases curtas.")
    pontos_fortes: list[str] = Field(min_length=1, max_length=5)
    pontos_fracos: list[str] = Field(min_length=1, max_length=5)
    sugestoes: list[str] = Field(min_length=1, max_length=5)

    def to_candidate_report(self, total_questions: int) -> CandidateReport:
        return CandidateReport(
            overall_summary=self.resumo,
            strengths=self.pontos_fortes,
            weaknesses=self.pontos_fracos,
            suggestions=self.sugestoes,
            total_questions=total_questions,
        )
