"""Rate limiting global da API via slowapi.

IP do cliente: primeiro valor de ``X-Forwarded-For`` (proxy/load balancer),
com fallback para ``request.client.host`` e, por último, ``127.0.0.1``.

O storage ``memory://`` mantém contadores apenas no processo atual; em deploy
multi-réplica cada instância aplica seu próprio limite (não há bucket compartilhado
entre pods/workers sem backend Redis ou equivalente).

O ``SlowAPIMiddleware`` padrão não resolve handlers em apps FastAPI (retorna ``None``
e isenta a rota), então usamos middleware próprio que aplica ``application_limits``
mesmo sem handler resolvido.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import _find_route_handler, async_check_limits
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.settings import settings

_RATE_LIMIT_EXCEEDED_DETAIL = "Muitas requisições. Tente novamente em instantes."
_RATE_LIMIT_EXCEEDED_CODE = "RATE_LIMIT_EXCEEDED"


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "127.0.0.1"


class _ApplicationRateLimitMiddleware(BaseHTTPMiddleware):
    """Aplica limites globais sem depender de handler resolvido (FastAPI)."""

    async def dispatch(self, request: Request, call_next):
        limiter: Limiter = request.app.state.limiter
        if not limiter.enabled:
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path == "/health":
            return await call_next(request)

        handler = _find_route_handler(request.app.routes, request.scope)
        if handler is not None:
            handler_name = f"{handler.__module__}.{handler.__name__}"
            if handler_name in limiter._exempt_routes:
                return await call_next(request)

        error_response, should_inject_headers = await async_check_limits(
            limiter, request, handler, request.app
        )
        if error_response is not None:
            return error_response

        response = await call_next(request)
        if should_inject_headers:
            response = limiter._inject_headers(response, request.state.view_rate_limit)
        return response


limiter = Limiter(
    key_func=get_client_ip,
    application_limits=[lambda: settings.RATE_LIMIT_GLOBAL],
    strategy="moving-window",
    storage_uri="memory://",
    headers_enabled=False,
    enabled=settings.RATE_LIMIT_ENABLED,
    swallow_errors=False,
)


async def _rate_limit_exceeded_handler(
    _request: Request, _exc: RateLimitExceeded
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": _RATE_LIMIT_EXCEEDED_DETAIL,
            "code": _RATE_LIMIT_EXCEEDED_CODE,
        },
    )


def setup_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(_ApplicationRateLimitMiddleware)
