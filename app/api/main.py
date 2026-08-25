import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.routers import auth, discovery, interviews
from app.core.domain.registry import (
    DomainEnum,
    DomainNotRegisteredError,
    get_cached_domain,
)
from app.core.logging import configure_logging
from app.core.settings import settings
from app.domains.async_messaging.bootstrap import register_async_messaging_domain

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.LOG_LEVEL)

    # Startup: registra todos os domínios disponíveis
    register_async_messaging_domain()
    for domain in DomainEnum:
        try:
            get_cached_domain(domain)
            logger.info(
                "Domain registered at startup",
                extra={"domain": domain.value},
            )
        except DomainNotRegisteredError:
            logger.warning(
                "Domain not registered at startup",
                extra={"domain": domain.value},
            )
    yield
    # Shutdown: nada a limpar por enquanto


app = FastAPI(title="Interview Agent API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
