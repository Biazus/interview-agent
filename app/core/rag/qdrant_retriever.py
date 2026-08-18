from app.core.domain.interfaces import Chunk
from app.core.rag.embeddings import EmbeddingProvider
from app.core.rag.vector_store import VectorStore


class QdrantRetriever:
    """
    Implementação genérica de Retriever sobre Qdrant. Reutilizável por
    qualquer domínio — a única diferença entre domínios é qual coleção
    consultar.
    """

    def __init__(
        self,
        collection_name: str,
        *,
        embedder: EmbeddingProvider | None = None,
        store: VectorStore | None = None,
    ) -> None:
        self._collection_name = collection_name
        if embedder is None or store is None:
            from app.core.rag.factory import get_embedding_provider, get_vector_store

            embedder = embedder or get_embedding_provider()
            store = store or get_vector_store()
        self._embedder = embedder
        self._store = store

    def retrieve(
        self, query: str, top_k: int = 5, topic: str | None = None
    ) -> list[Chunk]:
        query_vector = self._embedder.embed(query)
        results = self._store.search(
            self._collection_name, query_vector, top_k=top_k, topic=topic
        )
        return [
            Chunk(
                text=r["text"], source=r["source"], topic=r["topic"], score=r["score"]
            )
            for r in results
        ]
