import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from app.core.llm.exceptions import StructuredOutputError
from app.core.llm.interfaces import LLMResponse
from app.core.llm.requests import DEFAULT_MAX_OUTPUT_TOKENS, GenerateRequest
from app.core.llm.structured import generate_structured


class _SampleOutput(BaseModel):
    resumo: str = Field(min_length=1)
    items: list[str] = Field(min_length=1)


@pytest.mark.asyncio
async def test_generate_structured_validates_json():
    llm = MagicMock()
    payload = _SampleOutput(resumo="ok", items=["a", "b"])
    llm.generate = AsyncMock(
        return_value=MagicMock(text=json.dumps(payload.model_dump()))
    )

    result = await generate_structured(llm, "prompt", _SampleOutput)

    assert result.resumo == "ok"
    assert result.items == ["a", "b"]
    llm.generate.assert_awaited_once()
    request = llm.generate.await_args.args[0]
    assert isinstance(request, GenerateRequest)
    assert request.prompt == "prompt"
    assert request.response_format == {"type": "json_object"}
    assert request.max_output_tokens == DEFAULT_MAX_OUTPUT_TOKENS


@pytest.mark.asyncio
async def test_generate_structured_raises_on_invalid_schema():
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=MagicMock(text=json.dumps({"resumo": "ok", "items": []}))
    )

    with pytest.raises(StructuredOutputError):
        await generate_structured(llm, "prompt", _SampleOutput)


@pytest.mark.asyncio
async def test_generate_structured_raises_on_empty_response():
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=MagicMock(text=""))

    with pytest.raises(StructuredOutputError):
        await generate_structured(llm, "prompt", _SampleOutput)


@pytest.mark.asyncio
async def test_generate_structured_with_response_returns_model_and_llm_response():
    from app.core.llm.structured import generate_structured_with_response

    llm = MagicMock()
    payload = _SampleOutput(resumo="ok", items=["a", "b"])
    llm_response = LLMResponse(
        text=json.dumps(payload.model_dump()),
        provider="groq",
        model="llama-test",
        tokens_used=10,
    )
    llm.generate = AsyncMock(return_value=llm_response)

    model, response = await generate_structured_with_response(
        llm, "prompt", _SampleOutput
    )

    assert model.resumo == "ok"
    assert model.items == ["a", "b"]
    assert response is llm_response
    assert response.provider == "groq"


@pytest.mark.asyncio
async def test_generate_structured_delegates_and_returns_only_model(monkeypatch):
    expected_model = _SampleOutput(resumo="delegado", items=["x"])
    expected_response = LLMResponse(
        text='{"resumo": "delegado", "items": ["x"]}',
        provider="test",
        model="test",
    )

    async def fake_with_response(*args, **kwargs):
        return expected_model, expected_response

    monkeypatch.setattr(
        "app.core.llm.structured.generate_structured_with_response",
        fake_with_response,
    )

    llm = MagicMock()
    result = await generate_structured(llm, "prompt", _SampleOutput)

    assert result == expected_model
    assert result.resumo == "delegado"
