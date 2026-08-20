from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from app.core.domain.interfaces import QuestionBank, RAGRetriever, RubricProvider

""" 
Uso aqui factories, não instâncias prontas, 
para não pagar custo de inicialização de domínios que não estão em uso. 
"""


class DomainEnum(str, Enum):
    """Domínios de entrevista disponíveis no sistema."""

    ASYNC_MESSAGING = "async_messaging"
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


def register_domain(domain: DomainEnum, factory: Callable[[], DomainModule]) -> None:
    """Registra a factory de um domínio. Chamado uma vez, na inicialização do app."""
    _registry[domain] = factory


def clear_registry() -> None:
    """Limpa o registry. Destinado a testes que precisam de isolamento entre casos."""
    _registry.clear()


@lru_cache
def get_cached_domain(domain: DomainEnum) -> DomainModule:
    """Wrapper cacheado de get_domain para reutilização por request."""
    return get_domain(domain)


def get_domain(domain: DomainEnum) -> DomainModule:
    """Resolve e instancia o módulo de domínio solicitado.
    ps.: aqui chamamos factory() a cada invocação, ou seja, cada chamada gera
    uma nova instância dos objetos concretos. Isso é intencional por enquanto
    (mantém o registry sem estado e sem se preocupar com singleton),
    mas na prática, coisas como o RAGRetriever provavelmente vão querer manter
    uma conexão/cliente já aberto com o vector DB reutilizado entre chamadas.
    Vamos resolver isso com um cache simples (ex: functools.lru_cache na factory,
    ou um singleton controlado pelo próprio main.py do FastAPI via Depends)
    quando conectarmos isso ao FastAPI. Não é um problema no domínio isolado
    que estamos construindo agora.
    """
    factory = _registry.get(domain)
    if factory is None:
        raise DomainNotRegisteredError(domain)
    return factory()
