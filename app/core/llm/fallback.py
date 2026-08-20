import logging
from collections.abc import Awaitable, Callable
from typing import AsyncIterator, TypeVar

from app.core.llm.exceptions import LLMProviderError, TransientProviderError
from app.core.llm.interfaces import LLMProvider, LLMResponse
from app.core.llm.requests import GenerateRequest, StreamRequest
from app.core.logging import error_type

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FallbackLLMProvider:
    """Tenta cada provider em ordem; passa para o próximo em falhas transientes.

    Só ``TransientProviderError`` (rate limit, rede, 5xx) aciona o próximo provider.
    ``PermanentProviderError`` (auth, request inválido) interrompe a cadeia imediatamente.
    """

    name = "fallback_chain"

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("FallbackLLMProvider precisa de ao menos um provider")
        self._providers = providers

    def _provider_failure_extra(
        self, provider: LLMProvider, exc: LLMProviderError
    ) -> dict[str, str]:
        return {"provider": provider.name, "error_type": error_type(exc)}

    def _log_transient_failure(
        self, provider: LLMProvider, exc: TransientProviderError, message: str
    ) -> None:
        logger.warning(message, extra=self._provider_failure_extra(provider, exc))

    def _log_permanent_failure(
        self, provider: LLMProvider, exc: LLMProviderError, message: str
    ) -> None:
        logger.error(message, extra=self._provider_failure_extra(provider, exc))

    def _log_chain_exhausted(
        self, last_error: TransientProviderError | None, message: str
    ) -> None:
        logger.error(message, extra={"error_type": error_type(last_error)})

    async def _try_providers(
        self,
        operation: Callable[[LLMProvider], Awaitable[T]],
        *,
        transient_warning: str,
        permanent_error: str,
        exhausted_error: str,
        exhausted_message: str,
    ) -> T:
        last_error: TransientProviderError | None = None
        for provider in self._providers:
            try:
                return await operation(provider)
            except TransientProviderError as exc:
                self._log_transient_failure(provider, exc, transient_warning)
                last_error = exc
            except LLMProviderError as exc:
                self._log_permanent_failure(provider, exc, permanent_error)
                raise
        self._log_chain_exhausted(last_error, exhausted_error)
        raise LLMProviderError(
            f"{exhausted_message} "
            f"Último erro ({error_type(last_error)}): {last_error}"
        )

    async def generate(self, request: GenerateRequest) -> LLMResponse:
        return await self._try_providers(
            lambda provider: provider.generate(request),
            transient_warning="Provider failed, trying next in chain",
            permanent_error="Permanent provider error, aborting fallback chain",
            exhausted_error="All providers in fallback chain exhausted",
            exhausted_message="Todos os providers da cadeia falharam.",
        )

    async def stream(self, request: StreamRequest) -> AsyncIterator[str]:
        last_error: TransientProviderError | None = None
        for provider in self._providers:
            try:
                async for chunk in provider.stream(request):
                    yield chunk
                return
            except TransientProviderError as exc:
                self._log_transient_failure(
                    provider,
                    exc,
                    "Provider failed during streaming, trying next in chain",
                )
                last_error = exc
            except LLMProviderError as exc:
                self._log_permanent_failure(
                    provider,
                    exc,
                    "Permanent provider error during streaming, aborting fallback chain",
                )
                raise
        self._log_chain_exhausted(
            last_error,
            "All providers in fallback chain exhausted during streaming",
        )
        raise LLMProviderError(
            "Todos os providers da cadeia falharam no streaming. "
            f"Último erro ({error_type(last_error)}): {last_error}"
        )
