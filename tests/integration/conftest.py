import pytest
from qdrant_client import QdrantClient

from app.core.rag.qdrant_retriever import QdrantRetriever


@pytest.fixture(scope="session")
def qdrant_available() -> None:
    try:
        client = QdrantClient(host="localhost", port=6333)
        client.get_collections()
    except Exception:
        pytest.skip("Qdrant não está disponível em localhost:6333")


@pytest.fixture(scope="session")
def async_messaging_retriever(qdrant_available: None) -> QdrantRetriever:
    return QdrantRetriever("async_messaging")
