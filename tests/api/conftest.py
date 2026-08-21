import os
from collections.abc import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.api.main import app
from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.core.rag.seed_manifest import compute_manifest_hash
from app.domains.async_messaging import rag_config


def _ready_vector_store() -> MagicMock:
    store = MagicMock(spec=["get_collection_info"])
    store.get_collection_info.return_value = (
        100,
        {
            "seed_manifest_hash": compute_manifest_hash(
                rag_config.SEED_MANIFEST_FILES, EMBEDDING_MODEL_ID
            ),
            "embedding_model_id": EMBEDDING_MODEL_ID,
            "seed_manifest_files": list(rag_config.SEED_MANIFEST_FILES),
            "seeded_at": "2026-01-01T00:00:00Z",
        },
    )
    return store


@pytest.fixture(autouse=True)
def _default_rag_ready_for_api_tests():
    from app.core.rag.factory import clear_rag_cache

    clear_rag_cache()
    with patch(
        "app.core.rag.rag_readiness.get_vector_store",
        return_value=_ready_vector_store(),
    ):
        yield
    clear_rag_cache()


@pytest.fixture(autouse=True)
def _clear_domain_cache():
    from app.api.dependencies import get_llm_chain
    from app.core.domain.registry import get_cached_domain
    from app.core.rag.factory import clear_rag_cache

    clear_rag_cache()
    get_cached_domain.cache_clear()
    get_llm_chain.cache_clear()
    yield
    clear_rag_cache()
    get_cached_domain.cache_clear()
    get_llm_chain.cache_clear()


@pytest.fixture
def database_url() -> str:
    return os.environ["DATABASE_URL"]


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Registra candidato, faz login e retorna client com bearer token."""
    email = "candidato@test.example"
    password = "senha-segura-123"

    register_response = await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    client.headers.pop("Authorization", None)
