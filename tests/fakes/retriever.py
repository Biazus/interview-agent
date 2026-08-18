from app.core.domain.interfaces import Chunk


class FakeRAGRetriever:
    """Retriever determinístico para testes unitários (sem modelo nem Qdrant)."""

    def __init__(self, chunks: list[Chunk] | None = None) -> None:
        self._chunks = chunks or [
            Chunk(
                text="DLQ armazena mensagens que falharam após retries.",
                source="fake-dlq.md",
                topic="dead_letter_queue",
                score=1.0,
            )
        ]

    def retrieve(self, query: str, topic: str, top_k: int = 5) -> list[Chunk]:
        if topic:
            filtered = [c for c in self._chunks if c.topic == topic]
            return filtered[:top_k]
        return self._chunks[:top_k]
