from app.domains.async_messaging.bootstrap import register_async_messaging_domain


def bootstrap_domains() -> None:
    """Registra todos os domínios disponíveis. Idempotente — pode ser chamado a cada startup."""
    register_async_messaging_domain()


bootstrap_domains()
