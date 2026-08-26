import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.routers import auth, discovery, interviews
from app.core.domain.registry import (
    DomainEnum,
    get_cached_domain,
    list_registered_domains,
)
from app.core.logging import configure_logging
from app.core.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.LOG_LEVEL)

    # Startup: registra todos os domínios disponíveis
    import app.bootstrap

    app.bootstrap.bootstrap_domains()

    for domain_value in list_registered_domains():
        domain = DomainEnum(domain_value)
        get_cached_domain(domain)
        logger.info(
            "Domain warmed at startup",
            extra={"domain": domain.value},
        )
    yield
    # Shutdown: nada a limpar por enquanto


app = FastAPI(title="Interview Agent API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
register_error_handlers(app)

app.include_router(auth.router)
app.include_router(discovery.router)
app.include_router(interviews.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
