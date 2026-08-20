from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

pytest.importorskip(
    "app.core.auth.db_token_validator",
    reason="Fase 1 pendente: app.core.auth",
)

from app.core.auth.db_token_validator import DbTokenValidator  # noqa: E402
from app.core.auth.token import generate_token  # noqa: E402


class FakeAuthTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[str, tuple[UUID, datetime]] = {}

    def store(self, token_hash: str, candidate_id: UUID, expires_at: datetime) -> None:
        self._tokens[token_hash] = (candidate_id, expires_at)

    async def find_candidate_by_hash(
        self, token_hash: str
    ) -> tuple[UUID, datetime] | None:
        return self._tokens.get(token_hash)


@pytest.fixture
def candidate_id() -> UUID:
    return uuid4()


@pytest.fixture
def validator() -> DbTokenValidator:
    return DbTokenValidator(repository=FakeAuthTokenRepository())


@pytest.mark.asyncio
async def test_validate_returns_candidate_id_for_valid_token(
    validator: DbTokenValidator, candidate_id: UUID
):
    raw_token, token_hash = generate_token()
    validator._repository.store(
        token_hash, candidate_id, datetime.now(UTC) + timedelta(hours=1)
    )

    result = await validator.validate(raw_token)

    assert result == candidate_id


@pytest.mark.asyncio
async def test_validate_returns_none_for_unknown_token(validator: DbTokenValidator):
    result = await validator.validate("token-desconhecido")

    assert result is None


@pytest.mark.asyncio
async def test_validate_returns_none_for_expired_token(
    validator: DbTokenValidator, candidate_id: UUID
):
    raw_token, token_hash = generate_token()
    validator._repository.store(
        token_hash, candidate_id, datetime.now(UTC) - timedelta(seconds=1)
    )

    result = await validator.validate(raw_token)

    assert result is None
