import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_returns_201_without_access_token(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={"email": "novo@candidato.com", "password": "senha-segura-123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert "access_token" not in body
    assert "id" in body or "email" in body


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient):
    payload = {"email": "duplicado@candidato.com", "password": "senha-segura-123"}

    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)

    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "EMAIL_ALREADY_REGISTERED"
    assert isinstance(body["detail"], str)


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(client: AsyncClient):
    response = await client.post(
        "/auth/login",
        json={"email": "inexistente@candidato.com", "password": "senha-errada"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_returns_bearer_token_with_24h_ttl(client: AsyncClient):
    email = "login@candidato.com"
    password = "senha-segura-123"
    await client.post("/auth/register", json={"email": email, "password": password})

    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 86400


@pytest.mark.asyncio
async def test_protected_route_without_token_returns_401(client: AsyncClient):
    response = await client.get("/interviews/active")

    assert response.status_code == 401
    assert response.json()["code"] in {"MISSING_TOKEN", "INVALID_TOKEN"}


@pytest.mark.asyncio
async def test_password_validation(client: AsyncClient):
    payload = {"email": "test@candidato.com", "password": "good-password-123"}
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    payload = {"email": "test@candidato.com", "password": "123"}
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Dados inválidos na requisição."
    payload = {"email": "test@candidato.com", "password": "good-password-123" * 10}
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Dados inválidos na requisição."


@pytest.mark.asyncio
async def test_protected_route_with_invalid_token_returns_401(client: AsyncClient):
    response = await client.get(
        "/interviews/active",
        headers={"Authorization": "Bearer token-invalido"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"
