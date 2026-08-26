from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.domains.async_messaging.rag_config import build_rag_config
from tests.fakes.llm import DeterministicLLM

_START_PAYLOAD = {
    "domain": "async_messaging",
    "topic": "dead_letter_queue",
    "difficulty": 1,
}

RAG_NOT_READY_BODY = {
    "detail": "Base de conhecimento RAG indisponível. Execute o seed antes de iniciar entrevistas.",
    "code": "RAG_NOT_READY",
}


def _vector_store_empty() -> MagicMock:
    store = MagicMock(spec=["get_collection_info"])
    store.get_collection_info.return_value = (0, {})
    return store


def _vector_store_stale() -> MagicMock:
    rag_config = build_rag_config()
    store = MagicMock(spec=["get_collection_info"])
    store.get_collection_info.return_value = (
        100,
        {
            "seed_manifest_hash": "0" * 64,
            "embedding_model_id": EMBEDDING_MODEL_ID,
            "seed_manifest_files": list(rag_config.seed_manifest_files),
            "seeded_at": "2026-01-01T00:00:00Z",
        },
    )
    return store


@pytest.fixture
async def interview_client(authenticated_client: AsyncClient) -> AsyncClient:
    with patch("app.api.dependencies.get_llm_chain", lambda: DeterministicLLM()):
        yield authenticated_client


@pytest.mark.asyncio
async def test_start_interview_returns_503_when_qdrant_collection_empty(
    interview_client: AsyncClient,
):
    with patch(
        "app.core.rag.rag_readiness.get_vector_store",
        return_value=_vector_store_empty(),
    ):
        response = await interview_client.post("/interviews", json=_START_PAYLOAD)

    assert response.status_code == 503
    assert response.json() == RAG_NOT_READY_BODY


@pytest.mark.asyncio
async def test_start_interview_returns_503_when_manifest_stale(
    interview_client: AsyncClient,
):
    with patch(
        "app.core.rag.rag_readiness.get_vector_store",
        return_value=_vector_store_stale(),
    ):
        response = await interview_client.post("/interviews", json=_START_PAYLOAD)

    assert response.status_code == 503
    assert response.json() == RAG_NOT_READY_BODY


@pytest.mark.asyncio
async def test_rag_not_ready_is_distinct_from_invalid_topic(
    interview_client: AsyncClient,
):
    with patch(
        "app.core.rag.rag_readiness.get_vector_store",
        return_value=_vector_store_empty(),
    ):
        rag_response = await interview_client.post("/interviews", json=_START_PAYLOAD)

    invalid_topic_response = await interview_client.post(
        "/interviews",
        json={**_START_PAYLOAD, "topic": "nonexistent_topic"},
    )

    assert rag_response.status_code == 503
    assert rag_response.json()["code"] == "RAG_NOT_READY"
    assert invalid_topic_response.status_code == 400
    assert invalid_topic_response.json()["code"] == "INVALID_TOPIC"
    assert rag_response.json()["code"] != invalid_topic_response.json()["code"]
