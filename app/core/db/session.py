from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.engine import engine

async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)
