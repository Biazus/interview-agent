from functools import lru_cache

from app.core.domain.registry import DomainEnum, DomainModule, get_domain


@lru_cache
def get_active_domain() -> DomainModule:
    """
    Resolve o domínio ativo da entrevista.

    Por enquanto fixo em ASYNC_MESSAGING; quando houver múltiplos domínios
    ativos simultaneamente (ex: escolha por sessão de usuário), este ponto
    muda para ler de configuração/request em vez de constante.
    """
    return get_domain(DomainEnum.ASYNC_MESSAGING)
