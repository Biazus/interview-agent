from dataclasses import dataclass, field
from typing import Protocol

"""
Em RAG (Retrieval-Augmented Generation), você não joga um documento inteiro para o LLM buscar informação.
Isso estouraria o limite de contexto e sairia caro.
Em vez disso, o documento é dividido em pedaços menores (chunks) durante a ingestão,
cada chunk é transformado em um vetor numérico (embedding) que representa seu "significado",
e esses vetores ficam armazenados no banco vetorial. Quando alguém faz uma pergunta,
a pergunta também vira um vetor, e o banco vetorial retorna os chunks cujos vetores são mais "próximos"
(mais similares semanticamente) ao vetor da pergunta. 
Isso é o retrieval. Depois, esses chunks recuperados são inseridos no prompt do LLM como contexto,
para ele gerar uma resposta fundamentada neles (a parte "augmented generation")
"""

@dataclass(frozen=True)
class Chunk:
    """Um pedaço de texto recuperado do material de referência (RAG)."""
    text: str
    source: str          # ex: "aws-docs-sqs-dlq.md"
    topic: str            # ex: "dead_letter_queue"
    score: float = 0.0    # similaridade com a query (0 a 1, opcional na v1)


@dataclass(frozen=True)
class Question:
    """Uma pergunta de entrevista, com seus metadados de domínio."""
    id: str
    topic: str             # ex: "fan_out"
    difficulty: int        # ex: 1 (fácil) a 5 (difícil)
    prompt: str             # o texto da pergunta em si
    follow_up_of: str | None = None  # id da pergunta anterior, se for aprofundamento


@dataclass(frozen=True)
class RubricCriterion:
    """Um critério de avaliação dentro da rubrica de um tópico."""
    description: str
    weak_example: str
    medium_example: str
    strong_example: str


@dataclass(frozen=True)
class Rubric:
    """A rubrica completa de avaliação para um tópico."""
    topic: str
    criteria: list[RubricCriterion] = field(default_factory=list)


class RAGRetriever(Protocol):
    """Contrato para buscar material de referência relevante no domínio."""

    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]:
        ...


class QuestionBank(Protocol):
    """Contrato para consultar o banco de perguntas do domínio."""

    def next_question(self, topic: str, difficulty: int) -> Question:
        ...

    def topics(self) -> list[str]:
        """Lista os tópicos disponíveis neste domínio (ex: ['sqs', 'sns', 'lambda'])."""
        ...


class RubricProvider(Protocol):
    """Contrato para obter a rubrica de avaliação de um tópico."""

    def get_rubric(self, topic: str) -> Rubric:
        ...