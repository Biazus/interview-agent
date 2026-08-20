import os

# Satisfies pydantic Settings at import time; tests inject mock clients and never call APIs.
os.environ.setdefault("GROQ_API_KEY", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://interview:interview@localhost:5432/interview_agent_test",
)

import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture(scope="session", autouse=True)
def _ensure_database_schema() -> None:
    """Cria schema no banco de teste (interview_agent_test).

    Pré-requisitos:
      docker compose up -d postgres
      (opcional) uv run alembic upgrade head  # com DATABASE_URL apontando para test
    """

    async def setup() -> None:
        from app.core.db.base import Base
        from app.core.db import models  # noqa: F401

        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(setup())


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Transação por teste com rollback automático no teardown."""
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        poolclass=NullPool,
    )
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()
