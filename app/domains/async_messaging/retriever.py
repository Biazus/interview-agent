from app.core.domain.interfaces import Chunk


class FakeAsyncMessagingRetriever:
    """Implementação provisória do RAGRetriever, sem busca vetorial real ainda."""

    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]:
        return [
            Chunk(
                text="Uma DLQ (Dead Letter Queue) captura mensagens que falharam "
                "após o número máximo de tentativas de processamento.",
                source="fake-placeholder",
                topic="dead_letter_queue",
                score=0.0,
            )
        ][:top_k]
