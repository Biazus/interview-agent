from app.core.domain.interfaces import Chunk
from app.core.rag.embeddings import EmbeddingProvider
from app.core.rag.vector_store import VectorStore


class QdrantRetriever:
    """
    Implementação genérica de Retriever sobre Qdrant. Reutilizável por
    qualquer domínio — a única diferença entre domínios é qual coleção
    consultar.
    """

    def __init__(self, collection_name: str) -> None:
        self._collection_name = collection_name
        self._embedder = EmbeddingProvider()
        self._store = VectorStore()

    async def retrieve(self, query: str, top_k: int = 3) -> list[Chunk]:
        query_vector = self._embedder.embed(query)
        results = self._store.search(self._collection_name, query_vector, top_k=top_k)
        return [
            Chunk(
                text=r["text"], source=r["source"], topic=r["topic"], score=r["score"]
            )
            for r in results
        ]
