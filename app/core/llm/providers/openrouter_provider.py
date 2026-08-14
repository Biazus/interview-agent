from typing import AsyncIterator

from app.core.llm.interfaces import LLMProvider, LLMResponse


class OpenRouterProvider(LLMProvider):
    async def stream(self, prompt: str, **params) -> AsyncIterator[str]:
        ...

    async def generate(self, prompt: str, **params) -> LLMResponse:
        ...