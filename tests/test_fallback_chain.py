from unittest.mock import AsyncMock, MagicMock

import pytest
from groq import RateLimitError as GroqRateLimitError
from openai import RateLimitError as OpenAIRateLimitError

from app.core.llm.fallback import FallbackLLMProvider
from app.core.llm.providers.groq_provider import GroqProvider
from app.core.llm.providers.openrouter_provider import OpenRouterProvider


@pytest.mark.asyncio
async def test_fallback_moves_to_openrouter_when_groq_rate_limited():
    groq = GroqProvider()
    openrouter = OpenRouterProvider()

    # Groq falha com rate limit real do SDK
    groq.client.chat.completions.create = AsyncMock(
        side_effect=GroqRateLimitError(
            "limite excedido", response=MagicMock(), body=None
        )
    )

    # OpenRouter responde normalmente
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "resposta do openrouter"
    fake_response.model = "meta-llama/llama-3.3-70b-instruct:free"
    fake_response.usage.total_tokens = 17
    openrouter.client.chat.completions.create = AsyncMock(return_value=fake_response)

    chain = FallbackLLMProvider([groq, openrouter])
    result = await chain.generate("qualquer prompt")

    assert result.provider == "openrouter"
    assert result.text == "resposta do openrouter"

    # Testa que o Groq foi de fato tentado antes
    groq.client.chat.completions.create.assert_awaited_once()
    openrouter.client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_raises_when_all_providers_fail():
    groq = GroqProvider()
    openrouter = OpenRouterProvider()

    groq.client.chat.completions.create = AsyncMock(
        side_effect=GroqRateLimitError(
            "limite excedido", response=MagicMock(), body=None
        )
    )
    openrouter.client.chat.completions.create = AsyncMock(
        side_effect=OpenAIRateLimitError(
            "também indisponível", response=MagicMock(), body=None
        )
    )

    chain = FallbackLLMProvider([groq, openrouter])

    with pytest.raises(Exception):  # LLMProviderError
        await chain.generate("qualquer prompt")
