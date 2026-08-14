import logging
from typing import AsyncIterator

from app.core.llm.exceptions import LLMProviderError
from app.core.llm.interfaces import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class FallbackLLMProvider:
    """Tenta cada provider em ordem; passa para o próximo em caso de falha.
    -  *Chain of Responsibility*
    """

    name = "fallback_chain"

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("FallbackLLMProvider precisa de ao menos um provider")
        self._providers = providers

    async def generate(self, prompt: str, **params) -> LLMResponse:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                return await provider.generate(prompt, **params)
            except LLMProviderError as e:
                logger.warning(
                    f"Provider '{provider.name}' falhou: {e}. Tentando próximo."
                )
                last_error = e
                continue
        raise LLMProviderError(
            f"Todos os providers da cadeia falharam. Último erro: {last_error}"
        )

    async def stream(self, prompt: str, **params) -> AsyncIterator[str]:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                async for chunk in provider.stream(prompt, **params):
                    yield chunk
                return
            except LLMProviderError as e:
                logger.warning(
                    f"Provider '{provider.name}' falhou no streaming: {e}. Tentando próximo."
                )
                last_error = e
                continue
        raise LLMProviderError(
            f"Todos os providers da cadeia falharam no streaming. Último erro: {last_error}"
        )
