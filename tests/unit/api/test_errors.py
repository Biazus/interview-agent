import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

pytest.importorskip("app.api.errors", reason="Fase 1 pendente: app.api.errors")

from app.api.errors import APIError, register_error_handlers  # noqa: E402
from app.core.exceptions import InvalidDomain  # noqa: E402


def test_api_error_exposes_status_detail_and_code():
    error = APIError(
        status_code=409,
        detail="E-mail já cadastrado.",
        code="EMAIL_ALREADY_REGISTERED",
    )

    assert error.status_code == 409
    assert error.detail == "E-mail já cadastrado."
    assert error.code == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.asyncio
async def test_api_error_handler_returns_json_with_detail_and_code():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise APIError(
            status_code=400,
            detail="Domínio inválido.",
            code="INVALID_DOMAIN",
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Domínio inválido.",
        "code": "INVALID_DOMAIN",
    }


@pytest.mark.asyncio
async def test_app_error_handler_maps_domain_exceptions():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/invalid-domain")
    def invalid_domain():
        raise InvalidDomain()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/invalid-domain")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Domínio inválido.",
        "code": "INVALID_DOMAIN",
    }
