import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_domains_returns_async_messaging(client: AsyncClient):
    response = await client.get("/domains")

    assert response.status_code == 200
    domains = response.json()
    assert "async_messaging" in domains


@pytest.mark.asyncio
async def test_get_topics_with_valid_domain_returns_topic_list(client: AsyncClient):
    without_domain = await client.get("/topics")
    assert (
        without_domain.status_code == 400
    ), "Rota legada /topics ainda ativa; discovery nova exige ?domain="

    response = await client.get("/topics", params={"domain": "async_messaging"})

    assert response.status_code == 200
    topics = response.json()
    assert isinstance(topics, list)
    assert "dead_letter_queue" in topics


@pytest.mark.asyncio
async def test_get_topics_without_domain_returns_400(client: AsyncClient):
    response = await client.get("/topics")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_DOMAIN"


@pytest.mark.asyncio
async def test_get_topics_with_invalid_domain_returns_400(client: AsyncClient):
    response = await client.get("/topics", params={"domain": "dominio_inexistente"})

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_DOMAIN"
