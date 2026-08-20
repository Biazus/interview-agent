from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routers import auth, discovery, interviews
from app.core.domain.registry import (
    DomainEnum,
    DomainNotRegisteredError,
    get_cached_domain,
)
from app.domains.async_messaging.bootstrap import register_async_messaging_domain


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: registra todos os domínios disponíveis
    register_async_messaging_domain()
    for domain in DomainEnum:
        try:
            get_cached_domain(domain)
        except DomainNotRegisteredError:
            pass
    yield
    # Shutdown: nada a limpar por enquanto


app = FastAPI(title="Interview Agent API", lifespan=lifespan)
register_error_handlers(app)

app.include_router(auth.router)
app.include_router(discovery.router)
app.include_router(interviews.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
