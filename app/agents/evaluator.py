import asyncio
import logging
from functools import partial

from app.agents.evaluation_schema import EvaluationLLMOutput
from app.core.domain.interfaces import (
    Chunk,
    Evaluation,
    RAGRetriever,
    Rubric,
    RubricProvider,
)
from app.core.llm.interfaces import LLMProvider
from app.core.llm.structured import generate_structured_with_response

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Você é um avaliador técnico de entrevistas de system design.

Atribua uma nota global de 1 a 100 para a resposta do candidato e justifique em até 3 frases.
Use os exemplos Fraca / Média / Forte dos critérios como calibração:
- Fraca: nota entre 1 e 30
- Média: nota entre 31 e 69
- Forte: nota entre 70 e 100

Priorize correção sobre completude. Resposta correta mas incompleta = nota média.
Nota alta = correta com pelo menos um detalhe relevante além do básico.
Não exija cobrir todos os trade-offs do material de referência.

Responda SOMENTE com um objeto JSON válido, sem markdown nem texto fora do JSON.
Use exatamente estas chaves:

- "score": inteiro de 1 a 100
- "feedback": string com a justificativa (até 3 frases)
"""


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
        output, response = await generate_structured_with_response(
            self._llm,
            prompt,
            EvaluationLLMOutput,
            system_prompt=_SYSTEM_PROMPT,
        )
        return output.to_evaluation(topic=topic, raw_response=response)

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
            f"Pergunta feita ao candidato:\n{question}\n\n"
            f"Resposta do candidato:\n{answer}\n\n"
            f"Critérios de avaliação para este tópico:\n{criteria_text}\n\n"
            f"Material de referência:\n{context_text}"
        )
