from datetime import UTC, datetime
from uuid import UUID

from app.core.auth.token import hash_token
from app.repositories.auth_token_repository import AuthTokenRepository


class DbTokenValidator:
    def __init__(self, repository: AuthTokenRepository) -> None:
        self._repository = repository

    async def validate(self, raw_token: str) -> UUID | None:
        token_hash = hash_token(raw_token)
        result = await self._repository.find_candidate_by_hash(token_hash)
        if result is None:
            return None

        candidate_id, expires_at = result
        if expires_at < datetime.now(UTC):
            return None

        return candidate_id
