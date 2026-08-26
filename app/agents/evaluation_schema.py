from pydantic import BaseModel, Field

from app.core.domain.interfaces import Evaluation
from app.core.llm.interfaces import LLMResponse


class EvaluationLLMOutput(BaseModel):
    """Schema JSON esperado do Avaliador."""

    score: int = Field(ge=1, le=100, description="Nota global 1–100.")
    feedback: str = Field(min_length=1, description="Justificativa em até 3 frases.")

    def to_evaluation(self, topic: str, raw_response: LLMResponse) -> Evaluation:
        return Evaluation(
            topic=topic,
            score=self.score,
            feedback=self.feedback,
            raw_response=raw_response,
        )
