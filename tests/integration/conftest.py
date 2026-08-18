import pytest
from qdrant_client import QdrantClient

from app.core.rag.factory import clear_rag_cache, get_qdrant_retriever
from app.core.rag.qdrant_retriever import QdrantRetriever


@pytest.fixture(scope="session", autouse=True)
def _clear_rag_cache_after_session():
    yield
    clear_rag_cache()


@pytest.fixture(scope="session")
def qdrant_available() -> None:
    try:
        client = QdrantClient(host="localhost", port=6333)
        client.get_collections()
    except Exception:
        pytest.skip("Qdrant não está disponível em localhost:6333")


@pytest.fixture(scope="session")
def async_messaging_retriever(qdrant_available: None) -> QdrantRetriever:
    return get_qdrant_retriever("async_messaging")
