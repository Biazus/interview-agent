import os
from uuid import uuid4

import pytest
from qdrant_client import QdrantClient

from app.core.db.models import Candidate
from app.core.rag.factory import clear_rag_cache, get_qdrant_retriever
from app.core.rag.qdrant_retriever import QdrantRetriever
from app.repositories.interview_repository import InterviewRepository


def postgres_available() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return url.startswith("postgresql")


@pytest.fixture
def require_postgres():
    if not postgres_available():
        pytest.skip("DATABASE_URL Postgres não configurada")


@pytest.fixture
async def interview_repository_with_candidate(db_session):
    candidate = Candidate(
        email=f"integration-{uuid4()}@example.com",
        password_hash="hash",
    )
    db_session.add(candidate)
    await db_session.flush()
    yield InterviewRepository(db_session), candidate.id


@pytest.fixture(scope="session", autouse=True)
def _clear_rag_cache_after_session():
    yield
    clear_rag_cache()


@pytest.fixture(scope="session")
def qdrant_available() -> None:
    try:
        client = QdrantClient(host="localhost", port=6333)
        client.get_collections()
    except Exception:
        pytest.skip("Qdrant não está disponível em localhost:6333")


@pytest.fixture(scope="session")
def async_messaging_retriever(qdrant_available: None) -> QdrantRetriever:
    return get_qdrant_retriever("async_messaging")
