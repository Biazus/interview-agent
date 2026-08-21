from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ActiveInterviewExists,
    AppError,
    DomainRequired,
    DuplicateTurn,
    EmailAlreadyRegistered,
    EmptyAnswer,
    InterviewAlreadyFinished,
    InterviewNotFinished,
    InterviewNotFound,
    InvalidCredentials,
    InvalidDomain,
    InvalidToken,
    InvalidTopic,
    LLMUnavailable,
    MissingToken,
    NoActiveInterview,
    RagNotReady,
)

_APP_ERROR_STATUS: dict[type[AppError], int] = {
    ActiveInterviewExists: 409,
    InterviewNotFound: 404,
    NoActiveInterview: 404,
    InterviewAlreadyFinished: 409,
    InterviewNotFinished: 409,
    InvalidDomain: 400,
    DomainRequired: 400,
    InvalidTopic: 400,
    EmptyAnswer: 422,
    DuplicateTurn: 409,
    LLMUnavailable: 503,
    RagNotReady: 503,
    EmailAlreadyRegistered: 409,
    InvalidCredentials: 401,
    MissingToken: 401,
    InvalidToken: 401,
}


class APIError(Exception):
    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def _app_error_status(exc: AppError) -> int:
    for error_type, status_code in _APP_ERROR_STATUS.items():
        if isinstance(exc, error_type):
            return status_code
    return 500


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=_app_error_status(exc),
            content={"detail": str(exc), "code": exc.code},
        )

    @app.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        for error in exc.errors():
            loc = error.get("loc", ())
            if loc == ("body", "answer"):
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": "A resposta não pode ser vazia.",
                        "code": "EMPTY_ANSWER",
                    },
                )

        return JSONResponse(
            status_code=400,
            content={
                "detail": "Dados inválidos na requisição.",
                "code": "VALIDATION_ERROR",
            },
        )
