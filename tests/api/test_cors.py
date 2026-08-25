import pytest
from httpx import AsyncClient

ALLOWED_ORIGIN = "http://localhost:5173"
DISALLOWED_ORIGIN = "http://evil.example.com"


@pytest.mark.asyncio
async def test_preflight_options_returns_cors_headers(client: AsyncClient):
    response = await client.options(
        "/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert "GET" in response.headers.get("access-control-allow-methods", "")
    assert "Authorization" in response.headers.get("access-control-allow-headers", "")


@pytest.mark.asyncio
async def test_get_with_allowed_origin_returns_cors_header(client: AsyncClient):
    response = await client.get(
        "/domains",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


@pytest.mark.asyncio
async def test_get_with_disallowed_origin_omits_cors_header(client: AsyncClient):
    response = await client.get(
        "/domains",
        headers={"Origin": DISALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
