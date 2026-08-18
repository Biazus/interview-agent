from unittest.mock import AsyncMock, MagicMock

import pytest
from groq import APIStatusError, BadRequestError
from groq import RateLimitError as GroqRateLimitError
from openai import RateLimitError as OpenAIRateLimitError

from app.core.llm.exceptions import InvalidRequestError, LLMProviderError
from app.core.llm.fallback import FallbackLLMProvider
from app.core.llm.providers.groq_provider import GroqProvider
from app.core.llm.providers.openrouter_provider import OpenRouterProvider
from app.core.llm.requests import GenerateRequest


@pytest.mark.asyncio
async def test_fallback_moves_to_openrouter_when_groq_rate_limited():
    groq_client = MagicMock()
    groq_client.chat.completions.create = AsyncMock(
        side_effect=GroqRateLimitError(
            "limite excedido", response=MagicMock(), body=None
        )
    )
    groq = GroqProvider(client=groq_client)

    openrouter_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "resposta do openrouter"
    fake_response.model = "meta-llama/llama-3.3-70b-instruct:free"
    fake_response.usage.total_tokens = 17
    openrouter_client.chat.completions.create = AsyncMock(return_value=fake_response)
    openrouter = OpenRouterProvider(client=openrouter_client)

    chain = FallbackLLMProvider([groq, openrouter])
    result = await chain.generate(GenerateRequest.simple("qualquer prompt"))

    assert result.provider == "openrouter"
    assert result.text == "resposta do openrouter"

    groq_client.chat.completions.create.assert_awaited_once()
    openrouter_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_raises_when_all_providers_fail():
    groq_client = MagicMock()
    groq_client.chat.completions.create = AsyncMock(
        side_effect=GroqRateLimitError(
            "limite excedido", response=MagicMock(), body=None
        )
    )
    groq = GroqProvider(client=groq_client)

    openrouter_client = MagicMock()
    openrouter_client.chat.completions.create = AsyncMock(
        side_effect=OpenAIRateLimitError(
            "também indisponível", response=MagicMock(), body=None
        )
    )
    openrouter = OpenRouterProvider(client=openrouter_client)

    chain = FallbackLLMProvider([groq, openrouter])

    with pytest.raises(LLMProviderError):
        await chain.generate(GenerateRequest.simple("qualquer prompt"))


@pytest.mark.asyncio
async def test_fallback_moves_to_openrouter_on_groq_server_error():
    groq_response = MagicMock()
    groq_response.status_code = 500
    groq_response.request = MagicMock()
    groq_client = MagicMock()
    groq_client.chat.completions.create = AsyncMock(
        side_effect=APIStatusError("server error", response=groq_response, body=None)
    )
    groq = GroqProvider(client=groq_client)

    openrouter_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "resposta do openrouter"
    fake_response.model = "meta-llama/llama-3.3-70b-instruct:free"
    fake_response.usage.total_tokens = 10
    openrouter_client.chat.completions.create = AsyncMock(return_value=fake_response)
    openrouter = OpenRouterProvider(client=openrouter_client)

    chain = FallbackLLMProvider([groq, openrouter])
    result = await chain.generate(GenerateRequest.simple("qualquer prompt"))

    assert result.provider == "openrouter"
    openrouter_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_does_not_retry_on_invalid_request():
    groq_client = MagicMock()
    groq_client.chat.completions.create = AsyncMock(
        side_effect=BadRequestError("bad request", response=MagicMock(), body=None)
    )
    groq = GroqProvider(client=groq_client)

    openrouter_client = MagicMock()
    openrouter_client.chat.completions.create = AsyncMock()
    openrouter = OpenRouterProvider(client=openrouter_client)

    chain = FallbackLLMProvider([groq, openrouter])

    with pytest.raises(InvalidRequestError):
        await chain.generate(GenerateRequest.simple("qualquer prompt"))

    openrouter_client.chat.completions.create.assert_not_awaited()
