from dataclasses import dataclass, field
from typing import Protocol

from app.core.llm.interfaces import LLMResponse


@dataclass(frozen=True)
class SelectorDecision:
    next_topic: str
    next_difficulty: int


@dataclass(frozen=True)
class Chunk:
    """Um pedaço de texto recuperado do material de referência (RAG)."""

    text: str
    source: str  # ex: "aws-docs-sqs-dlq.md"
    topic: str  # ex: "dead_letter_queue"
    score: float = 0.0  # similaridade com a query (0 a 1, opcional na v1)


@dataclass(frozen=True)
class Question:
    """Uma pergunta de entrevista, com seus metadados de domínio."""

    id: str
    topic: str  # ex: "fan_out"
    difficulty: int  # ex: 1 (fácil) a 5 (difícil)
    prompt: str  # o texto da pergunta em si


@dataclass(frozen=True)
class RubricCriterion:
    """Um critério de avaliação dentro da rubrica de um tópico."""

    description: str
    weak_example: str
    medium_example: str
    strong_example: str


@dataclass(frozen=True)
class Evaluation:
    topic: str
    level: str  # "weak" | "medium" | "strong"
    feedback: str
    raw_response: LLMResponse  # qual provider respondeu, tokens, etc.


@dataclass(frozen=True)
class Rubric:
    """A rubrica completa de avaliação para um tópico."""

    topic: str
    criteria: list[RubricCriterion] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateReport:
    overall_summary: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    total_questions: int


@dataclass
class InterviewState:
    # TODO Separar InterviewSession (metadados + flags)
    # de InterviewHistory (append-only) facilitaria persistência e testes E2E depois.
    topic: str
    difficulty: int
    current_question: Question
    history: list[tuple[Question, Evaluation]] = field(default_factory=list)
    finished: bool = False
    report: CandidateReport | None = None


class Selector(Protocol):
    def decide(
        self, state: InterviewState, evaluation: Evaluation
    ) -> SelectorDecision: ...


class RAGRetriever(Protocol):
    """Contrato para buscar material de referência relevante no domínio."""

    def retrieve(self, query: str, topic: str, top_k: int = 5) -> list[Chunk]: ...


class QuestionBank(Protocol):
    """Contrato para consultar o banco de perguntas do domínio."""

    def next_question(
        self, topic: str, difficulty: int, exclude_ids: set[str] | None = None
    ) -> Question: ...

    def topics(self) -> list[str]:
        """Lista os tópicos disponíveis neste domínio (ex: ['sqs', 'sns', 'lambda'])."""
        ...


class RubricProvider(Protocol):
    """Contrato para obter a rubrica de avaliação de um tópico."""

    def get_rubric(self, topic: str) -> Rubric: ...
