import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.llm.exceptions import StructuredOutputError
from app.core.llm.interfaces import LLMProvider

T = TypeVar("T", bound=BaseModel)

_JSON_OBJECT_FORMAT = {"type": "json_object"}
_DEFAULT_MAX_OUTPUT_TOKENS = 1024


async def generate_structured(
    llm: LLMProvider,
    prompt: str,
    output_model: type[T],
    **params,
) -> T:
    """Gera saída JSON via LLM e valida contra um modelo Pydantic."""
    call_params = {
        "response_format": _JSON_OBJECT_FORMAT,
        "max_completion_tokens": _DEFAULT_MAX_OUTPUT_TOKENS,
        "max_tokens": _DEFAULT_MAX_OUTPUT_TOKENS,
        **params,
    }
    response = await llm.generate(prompt, **call_params)

    raw = (response.text or "").strip()
    if not raw:
        raise StructuredOutputError("LLM retornou resposta vazia.")

    try:
        return output_model.model_validate_json(raw)
    except ValidationError as exc:
        raise StructuredOutputError(
            f"JSON não conforma ao schema {output_model.__name__}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(f"Resposta não é JSON válido: {exc}") from exc
