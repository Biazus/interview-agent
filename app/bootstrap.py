from app.domains.async_messaging.bootstrap import register_async_messaging_domain
from app.domains.python_basics.bootstrap import register_python_basics_domain


def bootstrap_domains() -> None:
    """Registra todos os domínios disponíveis. Idempotente — pode ser chamado a cada startup."""
    register_async_messaging_domain()
    register_python_basics_domain()


bootstrap_domains()
