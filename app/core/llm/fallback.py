import logging
from typing import AsyncIterator

from app.core.llm.exceptions import LLMProviderError, TransientProviderError
from app.core.llm.interfaces import LLMProvider, LLMResponse
from app.core.llm.requests import GenerateRequest, StreamRequest

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

    async def generate(self, request: GenerateRequest) -> LLMResponse:
        last_error: TransientProviderError | None = None
        for provider in self._providers:
            try:
                return await provider.generate(request)
            except TransientProviderError as e:
                logger.warning(
                    f"Provider '{provider.name}' falhou: {e}. Tentando próximo."
                )
                last_error = e
                continue
        raise LLMProviderError(
            f"Todos os providers da cadeia falharam. "
            f"Último erro ({type(last_error).__name__}): {last_error}"
        )

    async def stream(self, request: StreamRequest) -> AsyncIterator[str]:
        last_error: TransientProviderError | None = None
        for provider in self._providers:
            try:
                async for chunk in provider.stream(request):
                    yield chunk
                return
            except TransientProviderError as e:
                logger.warning(
                    f"Provider '{provider.name}' falhou no streaming: {e}. Tentando próximo."
                )
                last_error = e
                continue
        raise LLMProviderError(
            f"Todos os providers da cadeia falharam no streaming. "
            f"Último erro ({type(last_error).__name__}): {last_error}"
        )
