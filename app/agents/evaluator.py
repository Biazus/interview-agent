import asyncio
from functools import partial

from app.core.domain.interfaces import (
    Chunk,
    Evaluation,
    RAGRetriever,
    Rubric,
    RubricProvider,
)
from app.core.llm.exceptions import LLMProviderError
from app.core.llm.interfaces import LLMProvider
from app.core.llm.requests import GenerateRequest

_LEVEL_MAP = {"FRACA": "weak", "MEDIA": "medium", "FORTE": "strong"}


class EvaluationParseError(LLMProviderError):
    """Resposta do LLM não segue o formato NIVEL/FEEDBACK esperado."""


class EvaluatorAgent:
    """Avalia a resposta do candidato contra a rubrica do tópico,
    usando trechos de referência recuperados via RAG como apoio ao LLM."""

    def __init__(
        self,
        llm: LLMProvider,
        retriever: RAGRetriever,
        rubric_provider: RubricProvider,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._rubric_provider = rubric_provider

    async def evaluate(self, topic: str, question: str, answer: str) -> Evaluation:
        rubric = self._rubric_provider.get_rubric(topic)
        chunks = await asyncio.to_thread(
            partial(self._retriever.retrieve, query=answer, top_k=3, topic=topic)
        )

        prompt = self._build_prompt(question, answer, rubric, chunks)
        response = await self._llm.generate(GenerateRequest.simple(prompt))
        level, feedback = self._parse_response(response.text)

        return Evaluation(
            topic=topic, level=level, feedback=feedback, raw_response=response
        )

    def _build_prompt(
        self, question: str, answer: str, rubric: Rubric, chunks: list[Chunk]
    ) -> str:
        criteria_text = "\n".join(
            f"- {c.description}\n"
            f"  Fraca: {c.weak_example}\n"
            f"  Média: {c.medium_example}\n"
            f"  Forte: {c.strong_example}"
            for c in rubric.criteria
        )
        context_text = "\n".join(f"- {c.text} (fonte: {c.source})" for c in chunks)

        return (
            "Você é um avaliador técnico de entrevistas de system design.\n\n"
            f"Pergunta feita ao candidato:\n{question}\n\n"
            f"Resposta do candidato:\n{answer}\n\n"
            f"Critérios de avaliação para este tópico:\n{criteria_text}\n\n"
            f"Material de referência:\n{context_text}\n\n"
            "Classifique a resposta como FRACA, MEDIA ou FORTE, e justifique.\n"
            "Responda exatamente neste formato:\n"
            "NIVEL: <FRACA|MEDIA|FORTE>\n"
            "FEEDBACK: <justificativa em até 3 frases>"
        )

    def _parse_response(self, text: str) -> tuple[str, str]:
        level: str | None = None
        feedback: str | None = None
        for line in text.splitlines():
            if line.upper().startswith("NIVEL:"):
                raw = line.split(":", 1)[1].strip().upper()
                level = _LEVEL_MAP.get(raw)
            elif line.upper().startswith("FEEDBACK:"):
                feedback = line.split(":", 1)[1].strip()
        if level is None:
            raise EvaluationParseError(
                "Resposta do avaliador sem NIVEL válido (FRACA|MEDIA|FORTE)."
            )
        if feedback is None:
            raise EvaluationParseError("Resposta do avaliador sem FEEDBACK.")
        return level, feedback
