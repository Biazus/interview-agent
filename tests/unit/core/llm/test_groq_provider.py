from unittest.mock import AsyncMock, MagicMock

import pytest
from groq import RateLimitError as GroqRateLimitError

from app.core.llm.exceptions import RateLimitError
from app.core.llm.providers.groq_provider import GroqProvider
from app.core.llm.requests import GenerateRequest


@pytest.mark.asyncio
async def test_generate_returns_llm_response():
    client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "resposta de teste"
    fake_response.model = "llama-3.3-70b-versatile"
    fake_response.usage.total_tokens = 42
    client.chat.completions.create = AsyncMock(return_value=fake_response)

    provider = GroqProvider(client=client)
    result = await provider.generate(GenerateRequest.simple("qualquer prompt"))

    assert result.text == "resposta de teste"
    assert result.provider == "groq"
    assert result.tokens_used == 42

    call_kwargs = client.chat.completions.create.await_args.kwargs
    assert call_kwargs["max_completion_tokens"] == 1024
    assert call_kwargs["messages"][1]["content"] == "qualquer prompt"


@pytest.mark.asyncio
async def test_generate_translates_rate_limit_error():
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=GroqRateLimitError(
            "limite excedido", response=MagicMock(), body=None
        )
    )

    provider = GroqProvider(client=client)

    with pytest.raises(RateLimitError):
        await provider.generate(GenerateRequest.simple("qualquer prompt"))
