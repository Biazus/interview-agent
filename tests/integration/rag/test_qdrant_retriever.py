import pytest

from app.core.rag.qdrant_retriever import QdrantRetriever

pytestmark = pytest.mark.integration


def test_retrieve_returns_chunks_for_dlq_query(
    async_messaging_retriever: QdrantRetriever,
):
    chunks = async_messaging_retriever.retrieve(
        query="o que é DLQ", top_k=5, topic="dead_letter_queue"
    )

    assert len(chunks) > 0
    assert all(c.topic == "dead_letter_queue" for c in chunks)
