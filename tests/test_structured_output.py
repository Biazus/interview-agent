import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from app.core.llm.exceptions import StructuredOutputError
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
    call_kwargs = llm.generate.await_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}
    assert call_kwargs["max_completion_tokens"] == 1024
    assert call_kwargs["max_tokens"] == 1024


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
