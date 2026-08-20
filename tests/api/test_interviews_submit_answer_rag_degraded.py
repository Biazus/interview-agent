from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.core.rag.seed_manifest import compute_manifest_hash
from app.domains.async_messaging import rag_config
from tests.fakes.llm import DeterministicLLM
from tests.fakes.retriever import FakeRAGRetriever

_START_PAYLOAD = {
    "domain": "async_messaging",
    "topic": "dead_letter_queue",
    "difficulty": 1,
}


def _ready_metadata() -> dict:
    return {
        "seed_manifest_hash": compute_manifest_hash(
            rag_config.SEED_MANIFEST_FILES, EMBEDDING_MODEL_ID
        ),
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "seed_manifest_files": list(rag_config.SEED_MANIFEST_FILES),
        "seeded_at": "2026-01-01T00:00:00Z",
    }


def _vector_store_ready() -> MagicMock:
    store = MagicMock(spec=["get_collection_info"])
    store.get_collection_info.return_value = (100, _ready_metadata())
    return store


def _vector_store_empty() -> MagicMock:
    store = MagicMock(spec=["get_collection_info"])
    store.get_collection_info.return_value = (0, {})
    return store


@pytest.fixture
async def interview_client(authenticated_client: AsyncClient) -> AsyncClient:
    with patch("app.api.dependencies.get_llm_chain", lambda: DeterministicLLM()):
        yield authenticated_client


@pytest.mark.asyncio
async def test_submit_answer_does_not_return_503_when_rag_unavailable_after_start(
    interview_client: AsyncClient,
):
    ready_store = _vector_store_ready()
    empty_store = _vector_store_empty()
    degraded_retriever = FakeRAGRetriever(chunks=[])

    with patch("app.core.rag.rag_readiness.get_vector_store", return_value=ready_store):
        start_response = await interview_client.post("/interviews", json=_START_PAYLOAD)

    assert start_response.status_code == 201, start_response.text
    interview_id = UUID(start_response.json()["interview_id"])

    with (
        patch("app.core.rag.rag_readiness.get_vector_store", return_value=empty_store),
        patch("app.core.rag.rag_readiness.check_rag_ready") as mock_check_rag_ready,
        patch(
            "app.domains.async_messaging.bootstrap.get_qdrant_retriever",
            return_value=degraded_retriever,
        ),
    ):
        answer_response = await interview_client.post(
            f"/interviews/{interview_id}/answers",
            json={"answer": "DLQ armazena mensagens que falharam após retries."},
        )

    mock_check_rag_ready.assert_not_called()
    assert answer_response.status_code == 200
    body = answer_response.json()
    assert body.get("code") != "RAG_NOT_READY"
    assert "interview_id" in body or body.get("finished") is not None


@pytest.mark.asyncio
async def test_submit_answer_continues_with_empty_retrieval_chunks(
    interview_client: AsyncClient,
):
    """Mid-session Qdrant degradation: evaluator runs without context, no 503."""
    ready_store = _vector_store_ready()
    empty_retriever = FakeRAGRetriever(chunks=[])

    with patch("app.core.rag.rag_readiness.get_vector_store", return_value=ready_store):
        start_response = await interview_client.post("/interviews", json=_START_PAYLOAD)

    assert start_response.status_code == 201
    interview_id = UUID(start_response.json()["interview_id"])

    with (
        patch(
            "app.core.rag.rag_readiness.get_vector_store",
            return_value=_vector_store_empty(),
        ),
        patch(
            "app.domains.async_messaging.bootstrap.get_qdrant_retriever",
            return_value=empty_retriever,
        ),
    ):
        answer_response = await interview_client.post(
            f"/interviews/{interview_id}/answers",
            json={"answer": "Resposta válida mesmo sem chunks RAG."},
        )

    assert answer_response.status_code == 200
    assert answer_response.status_code != 503
