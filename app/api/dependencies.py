from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import OrchestratorAgent
from app.agents.selector_naive import NaiveSelector
from app.core.exceptions import InvalidToken, MissingToken
from app.core.auth.db_token_validator import DbTokenValidator
from app.core.db.session import async_session_factory
from app.core.domain.registry import DomainEnum, DomainModule, get_cached_domain
from app.core.llm.bootstrap import build_default_llm_chain
from app.core.llm.fallback import FallbackLLMProvider
from app.repositories.auth_token_repository import AuthTokenRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.services.auth_service import AuthService
from app.services.discovery_service import DiscoveryService
from app.services.interview_service import InterviewService


def get_active_domain() -> DomainModule:
    """
    Resolve o domínio ativo da entrevista.

    Por enquanto fixo em ASYNC_MESSAGING; quando houver múltiplos domínios
    ativos simultaneamente (ex: escolha por sessão de usuário), este ponto
    muda para ler de configuração/request em vez de constante.
    """
    return get_cached_domain(DomainEnum.ASYNC_MESSAGING)


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


def _parse_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise MissingToken()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidToken()

    return token


async def get_current_candidate_id(
    authorization: Annotated[str | None, Header()] = None,
    validator: DbTokenValidator = Depends(get_token_validator),
) -> UUID:
    token = _parse_bearer_token(authorization)
    candidate_id = await validator.validate(token)
    if candidate_id is None:
        raise InvalidToken()

    return candidate_id
