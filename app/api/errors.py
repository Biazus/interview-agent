from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def register_error_handlers(app: FastAPI) -> None:
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
