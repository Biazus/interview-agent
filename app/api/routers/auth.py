from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_auth_service
from app.api.rate_limit import limiter
from app.api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.core.settings import settings
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.shared_limit(lambda: settings.RATE_LIMIT_AUTH, scope="auth")
async def register(
    request: Request,
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    candidate = await auth_service.register(body.email, body.password)
    return RegisterResponse(id=candidate.id, email=candidate.email)


@router.post("/login", response_model=TokenResponse)
@limiter.shared_limit(lambda: settings.RATE_LIMIT_AUTH, scope="auth")
async def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    access_token, expires_in = await auth_service.login(body.email, body.password)
    return TokenResponse(access_token=access_token, expires_in=expires_in)
