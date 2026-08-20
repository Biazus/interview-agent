import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.llm.exceptions import StructuredOutputError
from app.core.llm.interfaces import LLMProvider
from app.core.llm.requests import DEFAULT_MAX_OUTPUT_TOKENS, GenerateRequest

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_OBJECT_FORMAT = {"type": "json_object"}

_MAX_ERROR_DETAIL = 200


def _truncate_error(message: str) -> str:
    if len(message) <= _MAX_ERROR_DETAIL:
        return message
    return message[: _MAX_ERROR_DETAIL - 3] + "..."


def _log_structured_failure(schema: str, error_msg: str) -> None:
    logger.warning(
        "Structured output validation failed",
        extra={
            "schema": schema,
            "error": _truncate_error(error_msg),
        },
    )


async def generate_structured(
    llm: LLMProvider,
    prompt: str,
    output_model: type[T],
    *,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    model: str | None = None,
) -> T:
    """Gera saída JSON via LLM e valida contra um modelo Pydantic."""
    request_kwargs: dict = {
        "prompt": prompt,
        "response_format": _JSON_OBJECT_FORMAT,
        "max_output_tokens": max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
    }
    if system_prompt is not None:
        request_kwargs["system_prompt"] = system_prompt
    if temperature is not None:
        request_kwargs["temperature"] = temperature
    if model is not None:
        request_kwargs["model"] = model

    request = GenerateRequest(**request_kwargs)
    response = await llm.generate(request)

    raw = (response.text or "").strip()
    if not raw:
        error = StructuredOutputError("LLM retornou resposta vazia.")
        _log_structured_failure(output_model.__name__, str(error))
        raise error

    try:
        return output_model.model_validate_json(raw)
    except ValidationError as exc:
        error = StructuredOutputError(
            f"JSON não conforma ao schema {output_model.__name__}: {exc}"
        )
        _log_structured_failure(output_model.__name__, str(exc))
        raise error from exc
    except json.JSONDecodeError as exc:
        error = StructuredOutputError(f"Resposta não é JSON válido: {exc}")
        _log_structured_failure(output_model.__name__, str(exc))
        raise error from exc
