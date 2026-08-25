from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.models import AuthToken


class AuthTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, token_hash: str, candidate_id: UUID, expires_at: datetime
    ) -> AuthToken:
        auth_token = AuthToken(
            token_hash=token_hash,
            candidate_id=candidate_id,
            expires_at=expires_at,
        )
        self._session.add(auth_token)
        await self._session.flush()
        return auth_token

    async def delete_by_candidate_id(self, candidate_id: UUID) -> int:
        stmt = delete(AuthToken).where(AuthToken.candidate_id == candidate_id)
        result = await self._session.execute(stmt)
        return result.rowcount

    async def find_candidate_by_hash(
        self, token_hash: str
    ) -> tuple[UUID, datetime] | None:
        result = await self._session.execute(
            select(AuthToken.candidate_id, AuthToken.expires_at).where(
                AuthToken.token_hash == token_hash
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return row.candidate_id, row.expires_at
