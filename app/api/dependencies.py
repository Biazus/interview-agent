from collections.abc import AsyncGenerator
from functools import lru_cache
import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import OrchestratorAgent
from app.agents.selector_naive import NaiveSelector
from app.core.exceptions import InvalidToken, MissingToken
from app.core.auth.db_token_validator import DbTokenValidator
from app.core.db.session import async_session_factory
from app.core.domain.registry import DomainEnum, get_cached_domain
from app.core.llm.bootstrap import build_default_llm_chain
from app.core.llm.fallback import FallbackLLMProvider
from app.repositories.auth_token_repository import AuthTokenRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.services.auth_service import AuthService
from app.services.discovery_service import DiscoveryService
from app.services.interview_service import InterviewService

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_llm_chain() -> FallbackLLMProvider:
    return build_default_llm_chain()


def get_orchestrator(domain: DomainEnum) -> OrchestratorAgent:
    module = get_cached_domain(domain)
    return OrchestratorAgent(
        domain=module,
        llm=get_llm_chain(),
        selector=NaiveSelector(module),
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Sessão por request: commit no sucesso, rollback em qualquer exceção."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]


def _candidate_repository(session: AsyncSession) -> CandidateRepository:
    return CandidateRepository(session)


def _auth_token_repository(session: AsyncSession) -> AuthTokenRepository:
    return AuthTokenRepository(session)


def get_discovery_service() -> DiscoveryService:
    return DiscoveryService()


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(
        candidate_repository=_candidate_repository(session),
        auth_token_repository=_auth_token_repository(session),
    )


def get_interview_service(session: DbSession) -> InterviewService:
    return InterviewService(
        repository=InterviewRepository(session),
        session=session,
        orchestrator_factory=get_orchestrator,
    )


def get_token_validator(session: DbSession) -> DbTokenValidator:
    return DbTokenValidator(repository=_auth_token_repository(session))


async def get_current_candidate_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    validator: DbTokenValidator = Depends(get_token_validator),
) -> UUID:
    if credentials is None:
        raise MissingToken()

    candidate_id = await validator.validate(credentials.credentials)
    if candidate_id is None:
        logger.warning(
            "Invalid authentication token",
            extra={"reason": "invalid_or_expired_token"},
        )
        raise InvalidToken()

    return candidate_id
