import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.api.main import app


@pytest.fixture(autouse=True)
def _clear_domain_cache():
    from app.api.dependencies import get_llm_chain
    from app.core.domain.registry import get_cached_domain

    get_cached_domain.cache_clear()
    get_llm_chain.cache_clear()
    yield
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
