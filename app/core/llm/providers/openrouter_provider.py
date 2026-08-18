from typing import AsyncIterator

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

from app.core.llm.config import settings
from app.core.llm.exceptions import ProviderUnavailableError, RateLimitError
from app.core.llm.interfaces import LLMResponse

_MODEL = "nvidia/nemotron-3.5-lightning:free"
_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self.client = client or AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=_BASE_URL,
        )

    async def generate(self, prompt: str, **params) -> LLMResponse:
        # TODO: remover system prompt genérico e passar como parâmetro
        create_kwargs: dict = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "model": params.get("model", _MODEL),
            "temperature": params.get("temperature", 0.5),
            "max_tokens": params.get("max_tokens", 1024),
            "stream": False,
        }
        if "response_format" in params:
            create_kwargs["response_format"] = params["response_format"]
        try:
            response = await self.client.chat.completions.create(**create_kwargs)
        except OpenAIRateLimitError as e:
            raise RateLimitError(f"OpenRouter rate limit: {e}") from e
        except (APIConnectionError, APITimeoutError) as e:
            raise ProviderUnavailableError(f"OpenRouter indisponível: {e}") from e

        content = response.choices[0].message.content or ""
        return LLMResponse(
            text=content,
            provider=self.name,
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else None,
        )

    async def stream(self, prompt: str, **params) -> AsyncIterator[str]:
        try:
            stream = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                model=params.get("model", _MODEL),
                temperature=params.get("temperature", 0.5),
                max_tokens=params.get("max_tokens", 1024),
                stream=True,
            )
        except OpenAIRateLimitError as e:
            raise RateLimitError(f"OpenRouter rate limit: {e}") from e
        except (APIConnectionError, APITimeoutError) as e:
            raise ProviderUnavailableError(f"OpenRouter indisponível: {e}") from e

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
