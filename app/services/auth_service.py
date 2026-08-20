from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.core.auth.password import hash_password, verify_password
from app.core.auth.token import generate_token
from app.core.db.models import Candidate
from app.core.exceptions import EmailAlreadyRegistered, InvalidCredentials
from app.core.settings import settings
from app.repositories.auth_token_repository import AuthTokenRepository
from app.repositories.candidate_repository import CandidateRepository


def _normalize_email(email: str) -> str:
    return email.lower().strip()


class AuthService:
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        auth_token_repository: AuthTokenRepository,
    ) -> None:
        self._candidate_repository = candidate_repository
        self._auth_token_repository = auth_token_repository

    async def register(self, email: str, password: str) -> Candidate:
        normalized_email = _normalize_email(email)
        password_hash = hash_password(password)

        try:
            return await self._candidate_repository.create(
                normalized_email, password_hash
            )
        except IntegrityError as exc:
            await self._candidate_repository.rollback()
            raise EmailAlreadyRegistered() from exc

    async def login(self, email: str, password: str) -> tuple[str, int]:
        normalized_email = _normalize_email(email)
        candidate = await self._candidate_repository.find_by_email(normalized_email)

        if candidate is None or not verify_password(password, candidate.password_hash):
            raise InvalidCredentials()

        raw_token, token_hash = generate_token()
        expires_at = datetime.now(UTC) + timedelta(
            seconds=settings.AUTH_TOKEN_TTL_SECONDS
        )
        await self._auth_token_repository.create(token_hash, candidate.id, expires_at)

        return raw_token, settings.AUTH_TOKEN_TTL_SECONDS
