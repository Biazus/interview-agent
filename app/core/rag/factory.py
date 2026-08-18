from functools import lru_cache

from app.core.rag.embeddings import EmbeddingProvider
from app.core.rag.qdrant_retriever import QdrantRetriever
from app.core.rag.vector_store import VectorStore


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return EmbeddingProvider()


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()


@lru_cache
def get_qdrant_retriever(collection_name: str) -> QdrantRetriever:
    return QdrantRetriever(
        collection_name,
        embedder=get_embedding_provider(),
        store=get_vector_store(),
    )


def clear_rag_cache() -> None:
    """Limpa singletons RAG. Destinado a testes e reinicialização explícita."""
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    get_qdrant_retriever.cache_clear()
