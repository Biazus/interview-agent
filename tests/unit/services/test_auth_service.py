from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.core.auth.password import hash_password
from app.core.auth.token import generate_token, hash_token
from app.core.db.models import AuthToken, Candidate
from app.core.exceptions import InvalidCredentials
from app.services.auth_service import AuthService


class FakeCandidateRepository:
    def __init__(self) -> None:
        self.candidates: dict[str, Candidate] = {}

    async def find_by_email(self, email: str) -> Candidate | None:
        return self.candidates.get(email.lower().strip())

    def register(self, email: str, password: str) -> Candidate:
        normalized_email = email.lower().strip()
        candidate = Candidate(
            id=uuid4(),
            email=normalized_email,
            password_hash=hash_password(password),
        )
        self.candidates[normalized_email] = candidate
        return candidate


class FakeAuthTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[str, tuple[UUID, datetime]] = {}
        self.call_log: list[str] = []

    def store(self, token_hash: str, candidate_id: UUID, expires_at: datetime) -> None:
        self._tokens[token_hash] = (candidate_id, expires_at)

    def token_count_for(self, candidate_id: UUID) -> int:
        return sum(1 for cid, _ in self._tokens.values() if cid == candidate_id)

    async def create(
        self, token_hash: str, candidate_id: UUID, expires_at: datetime
    ) -> AuthToken:
        self._tokens[token_hash] = (candidate_id, expires_at)
        self.call_log.append("create")
        return AuthToken(
            token_hash=token_hash,
            candidate_id=candidate_id,
            expires_at=expires_at,
        )

    async def delete_by_candidate_id(self, candidate_id: UUID) -> int:
        to_remove = [
            token_hash
            for token_hash, (cid, _) in self._tokens.items()
            if cid == candidate_id
        ]
        for token_hash in to_remove:
            del self._tokens[token_hash]
        self.call_log.append("delete_by_candidate_id")
        return len(to_remove)


class FailingCreateAuthTokenRepository(FakeAuthTokenRepository):
    def __init__(self) -> None:
        super().__init__()
        self._backup: dict[str, tuple[UUID, datetime]] = {}

    async def delete_by_candidate_id(self, candidate_id: UUID) -> int:
        self._backup = dict(self._tokens)
        return await super().delete_by_candidate_id(candidate_id)

    async def create(
        self, token_hash: str, candidate_id: UUID, expires_at: datetime
    ) -> AuthToken:
        self.call_log.append("create")
        self._tokens = dict(self._backup)
        raise RuntimeError("create failed")


@pytest.fixture
def candidate_repo() -> FakeCandidateRepository:
    return FakeCandidateRepository()


@pytest.fixture
def token_repo() -> FakeAuthTokenRepository:
    return FakeAuthTokenRepository()


@pytest.fixture
def auth_service(
    candidate_repo: FakeCandidateRepository,
    token_repo: FakeAuthTokenRepository,
) -> AuthService:
    return AuthService(
        candidate_repository=candidate_repo,
        auth_token_repository=token_repo,
    )


@pytest.mark.asyncio
async def test_login_revokes_existing_tokens_before_creating_new(
    auth_service: AuthService,
    candidate_repo: FakeCandidateRepository,
    token_repo: FakeAuthTokenRepository,
):
    candidate = candidate_repo.register("user@example.com", "senha-segura-123")
    old_raw_token, old_token_hash = generate_token()
    token_repo.store(
        old_token_hash,
        candidate.id,
        datetime.now(UTC) + timedelta(hours=1),
    )

    new_raw_token, expires_in = await auth_service.login(
        "user@example.com", "senha-segura-123"
    )

    assert token_repo.call_log == ["delete_by_candidate_id", "create"]
    assert token_repo.token_count_for(candidate.id) == 1
    assert new_raw_token != old_raw_token
    assert hash_token(new_raw_token) in token_repo._tokens
    assert old_token_hash not in token_repo._tokens
    assert expires_in == 86400


@pytest.mark.asyncio
async def test_login_succeeds_when_no_prior_tokens(
    auth_service: AuthService,
    candidate_repo: FakeCandidateRepository,
    token_repo: FakeAuthTokenRepository,
):
    candidate = candidate_repo.register("novo@example.com", "senha-segura-123")

    raw_token, expires_in = await auth_service.login(
        "novo@example.com", "senha-segura-123"
    )

    assert token_repo.call_log == ["delete_by_candidate_id", "create"]
    assert token_repo.token_count_for(candidate.id) == 1
    assert isinstance(raw_token, str)
    assert raw_token
    assert expires_in == 86400


@pytest.mark.asyncio
async def test_login_raises_invalid_credentials_without_touching_tokens(
    auth_service: AuthService,
    candidate_repo: FakeCandidateRepository,
    token_repo: FakeAuthTokenRepository,
):
    candidate_repo.register("user@example.com", "senha-segura-123")
    token_repo.store(
        "existing-hash",
        uuid4(),
        datetime.now(UTC) + timedelta(hours=1),
    )

    with pytest.raises(InvalidCredentials):
        await auth_service.login("user@example.com", "senha-errada")

    assert token_repo.call_log == []


@pytest.mark.asyncio
async def test_login_does_not_revoke_other_candidates_tokens(
    auth_service: AuthService,
    candidate_repo: FakeCandidateRepository,
    token_repo: FakeAuthTokenRepository,
):
    candidate_a = candidate_repo.register("a@example.com", "senha-segura-123")
    candidate_b = candidate_repo.register("b@example.com", "senha-segura-123")
    token_repo.store(
        "hash-a",
        candidate_a.id,
        datetime.now(UTC) + timedelta(hours=1),
    )
    token_repo.store(
        "hash-b",
        candidate_b.id,
        datetime.now(UTC) + timedelta(hours=1),
    )

    await auth_service.login("a@example.com", "senha-segura-123")

    assert token_repo.token_count_for(candidate_a.id) == 1
    assert token_repo.token_count_for(candidate_b.id) == 1
    assert "hash-b" in token_repo._tokens


@pytest.mark.asyncio
async def test_login_failure_on_create_preserves_existing_tokens(
    candidate_repo: FakeCandidateRepository,
):
    token_repo = FailingCreateAuthTokenRepository()
    auth_service = AuthService(
        candidate_repository=candidate_repo,
        auth_token_repository=token_repo,
    )
    candidate = candidate_repo.register("user@example.com", "senha-segura-123")
    old_raw_token, old_token_hash = generate_token()
    token_repo.store(
        old_token_hash,
        candidate.id,
        datetime.now(UTC) + timedelta(hours=1),
    )

    with pytest.raises(RuntimeError, match="create failed"):
        await auth_service.login("user@example.com", "senha-segura-123")

    assert token_repo.token_count_for(candidate.id) == 1
    assert old_token_hash in token_repo._tokens
