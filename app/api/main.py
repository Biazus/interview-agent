from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api.dependencies import get_active_domain
from app.core.domain.registry import DomainModule
from app.domains.async_messaging.bootstrap import register_async_messaging_domain


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: registra todos os domínios disponíveis
    register_async_messaging_domain()
    yield
    # Shutdown: nada a limpar por enquanto


app = FastAPI(title="Interview Agent API", lifespan=lifespan)


app = FastAPI(title="Interview Agent API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/topics")
def list_topics(domain: DomainModule = Depends(get_active_domain)) -> list[str]:
    """Rota de smoke test: prova que o domínio resolvido via DI está funcionando."""
    return domain.question_bank.topics()
