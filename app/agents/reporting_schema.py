from pydantic import BaseModel, Field, model_validator

from app.core.domain.interfaces import CandidateReport

_EMPTY_LIST_DEFAULTS: dict[str, str] = {
    "pontos_fortes": "Nenhum ponto forte claro identificado nesta entrevista.",
    "pontos_fracos": "Foram observadas lacunas nas respostas avaliadas.",
    "sugestoes": "Revisar os fundamentos dos tópicos abordados.",
}


class ReportLLMOutput(BaseModel):
    """Schema JSON esperado do Relator."""

    resumo: str = Field(min_length=1, description="Até 2 frases curtas.")
    pontos_fortes: list[str] = Field(min_length=1, max_length=5)
    pontos_fracos: list[str] = Field(min_length=1, max_length=5)
    sugestoes: list[str] = Field(min_length=1, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_lists(cls, data: object) -> object:
        """O LLM às vezes retorna arrays vazios; preenchemos com fallback legível."""
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        for field, default in _EMPTY_LIST_DEFAULTS.items():
            if normalized.get(field) == []:
                normalized[field] = [default]
        return normalized

    def to_candidate_report(self, total_questions: int) -> CandidateReport:
        return CandidateReport(
            overall_summary=self.resumo,
            strengths=self.pontos_fortes,
            weaknesses=self.pontos_fracos,
            suggestions=self.sugestoes,
            total_questions=total_questions,
        )
