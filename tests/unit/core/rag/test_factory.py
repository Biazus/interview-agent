from unittest.mock import MagicMock, patch

import pytest

from app.core.rag.factory import (
    clear_rag_cache,
    get_embedding_provider,
    get_qdrant_retriever,
    get_vector_store,
)


@pytest.fixture(autouse=True)
def _reset_rag_cache():
    clear_rag_cache()
    yield
    clear_rag_cache()


def test_get_embedding_provider_returns_same_instance():
    mock_embedder = MagicMock()
    with patch("app.core.rag.factory.EmbeddingProvider", return_value=mock_embedder):
        first = get_embedding_provider()
        second = get_embedding_provider()

    assert first is second
    assert first is mock_embedder


def test_get_vector_store_returns_same_instance():
    mock_store = MagicMock()
    with patch("app.core.rag.factory.VectorStore", return_value=mock_store):
        first = get_vector_store()
        second = get_vector_store()

    assert first is second
    assert first is mock_store


def test_get_qdrant_retriever_caches_by_collection():
    created: list[str] = []

    def make_retriever(collection_name: str, **kwargs: object) -> MagicMock:
        created.append(collection_name)
        return MagicMock(collection_name=collection_name)

    with (
        patch("app.core.rag.factory.EmbeddingProvider", return_value=MagicMock()),
        patch("app.core.rag.factory.VectorStore", return_value=MagicMock()),
        patch("app.core.rag.factory.QdrantRetriever", side_effect=make_retriever),
    ):
        first = get_qdrant_retriever("async_messaging")
        second = get_qdrant_retriever("async_messaging")
        other = get_qdrant_retriever("other_collection")

    assert first is second
    assert first is not other
    assert created == ["async_messaging", "other_collection"]


def test_clear_rag_cache_allows_new_instances():
    instances: list[MagicMock] = []

    with patch("app.core.rag.factory.EmbeddingProvider") as mock_cls:
        mock_cls.side_effect = lambda: instances.append(MagicMock()) or instances[-1]

        first = get_embedding_provider()
        clear_rag_cache()
        second = get_embedding_provider()

    assert first is not second
    assert len(instances) == 2
