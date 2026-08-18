from typing import AsyncIterator

from groq import APIConnectionError, APITimeoutError, AsyncGroq
from groq import RateLimitError as GroqRateLimitError

from app.core.llm.config import settings
from app.core.llm.exceptions import (
    LLMProviderError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.core.llm.interfaces import LLMProvider, LLMResponse

_MODEL = "openai/gpt-oss-safeguard-20b"
_MAX_COMPLETION_TOKENS = 512


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, client: AsyncGroq | None = None) -> None:
        self.client = client or AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def generate(self, prompt: str, **params) -> LLMResponse:
        create_kwargs: dict = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "model": _MODEL,
            "temperature": params.get("temperature", 0.5),
            "max_completion_tokens": params.get(
                "max_completion_tokens", _MAX_COMPLETION_TOKENS
            ),
            "top_p": 1,
            "stop": None,
            "stream": False,
        }
        if "response_format" in params:
            create_kwargs["response_format"] = params["response_format"]
        try:
            response = await self.client.chat.completions.create(**create_kwargs)
        except GroqRateLimitError as e:
            raise RateLimitError(f"Groq rate limit: {e}") from e

        except (APIConnectionError, APITimeoutError) as e:
            raise ProviderUnavailableError(f"Groq indisponível: {e}") from e

        choice = response.choices[0].message.content or ""
        return LLMResponse(
            text=choice,
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
                model=_MODEL,
                temperature=0.5,
                max_completion_tokens=params.get(
                    "max_completion_tokens", _MAX_COMPLETION_TOKENS
                ),
                top_p=1,
                stop=None,
                stream=True,
            )
        except GroqRateLimitError as e:
            raise RateLimitError(f"Groq rate limit: {e}") from e
        except (APIConnectionError, APITimeoutError) as e:
            raise ProviderUnavailableError(f"Groq indisponível: {e}") from e

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
