from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.models import Candidate


class CandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, email: str, password_hash: str) -> Candidate:
        candidate = Candidate(email=email, password_hash=password_hash)
        self._session.add(candidate)
        await self._session.flush()
        return candidate

    async def rollback(self) -> None:
        await self._session.rollback()

    async def find_by_email(self, email: str) -> Candidate | None:
        result = await self._session.execute(
            select(Candidate).where(Candidate.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, candidate_id: UUID) -> Candidate | None:
        result = await self._session.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        return result.scalar_one_or_none()
