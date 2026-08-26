from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from app.core.domain.interfaces import QuestionBank, RAGRetriever, RubricProvider
from app.core.domain.rag_config import DomainRagConfig

""" 
Uso aqui factories, não instâncias prontas, 
para não pagar custo de inicialização de domínios que não estão em uso. 
"""


class DomainEnum(str, Enum):
    """Domínios de entrevista disponíveis no sistema."""

    ASYNC_MESSAGING = "async_messaging"
    # test-only
    FAKE_TEST = "fake_test"
    FAKE_TEST_TWO = "fake_test_two"
    # futuro: KAFKA = "kafka", RABBITMQ = "rabbitmq", etc.


@dataclass(frozen=True)
class DomainModule:
    """Agrega as três dependências de domínio que o orquestrador precisa,
    sem conhecer suas implementações concretas."""

    retriever: RAGRetriever
    question_bank: QuestionBank
    rubric_provider: RubricProvider


class DomainNotRegisteredError(Exception):
    """Levantado quando um domínio solicitado não está no registry."""

    def __init__(self, domain: DomainEnum):
        self.domain = domain
        super().__init__(
            f"Domínio '{domain.value}' não está registrado. "
            f"Domínios disponíveis: {[d.value for d in _registry]}"
        )


_registry: dict[DomainEnum, Callable[[], DomainModule]] = {}
_rag_configs: dict[DomainEnum, DomainRagConfig] = {}


def register_domain(
    domain: DomainEnum,
    factory: Callable[[], DomainModule],
    rag_config: DomainRagConfig,
) -> None:
    """Registra a factory de um domínio. Chamado uma vez, na inicialização do app."""
    if not rag_config.collection_name:
        raise ValueError("collection_name must be non-empty")
    if not rag_config.seed_manifest_files:
        raise ValueError("seed_manifest_files must be non-empty")
    _registry[domain] = factory
    _rag_configs[domain] = rag_config


def get_domain_rag_config(domain: DomainEnum) -> DomainRagConfig:
    config = _rag_configs.get(domain)
    if config is None:
        raise DomainNotRegisteredError(domain)
    return config


def clear_registry() -> None:
    """Limpa o registry. Destinado a testes que precisam de isolamento entre casos."""
    _registry.clear()
    _rag_configs.clear()
    get_cached_domain.cache_clear()


def list_registered_domains() -> list[str]:
    """Retorna os valores de domínio efetivamente registrados no registry."""
    return [domain.value for domain in _registry]


@lru_cache
def get_cached_domain(domain: DomainEnum) -> DomainModule:
    """Wrapper cacheado de get_domain para reutilização por request."""
    return get_domain(domain)


def get_domain(domain: DomainEnum) -> DomainModule:
    """Resolve e instancia o módulo de domínio solicitado.

    Chama factory() a cada invocação. Para reutilização entre chamadas no mesmo
    processo, use get_cached_domain (cache por DomainEnum). Recursos pesados
    (ex.: QdrantRetriever) já são cacheados nas factories via @lru_cache
    (ver get_qdrant_retriever).
    """
    factory = _registry.get(domain)
    if factory is None:
        raise DomainNotRegisteredError(domain)
    return factory()
