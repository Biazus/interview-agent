from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from app.core.llm.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    LLMProviderError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.core.llm.interfaces import LLMResponse
from app.core.llm.requests import ChatRequest, GenerateRequest, StreamRequest


@dataclass(frozen=True)
class SdkErrorTypes:
    rate_limit: type[Exception]
    connection: tuple[type[Exception], ...]
    authentication: type[Exception]
    bad_request: type[Exception]
    api_status: type[Exception]


class ChatCompletionsAdapter(ABC):
    """Adapter base para APIs chat/completions (OpenAI-compatible).

    Subclasses implementam só o mapeamento de kwargs do SDK e tipos de exceção;
    generate/stream, mensagens, resposta e tradução de erros ficam centralizados.
    """

    name: str
    default_model: str

    def __init__(self, client: Any) -> None:
        self.client = client

    @abstractmethod
    def _sdk_error_types(self) -> SdkErrorTypes: ...

    @abstractmethod
    def _build_create_kwargs(
        self, request: ChatRequest, stream: bool
    ) -> dict[str, Any]: ...

    def _build_messages(self, request: ChatRequest) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt},
        ]

    def _map_sdk_error(self, exc: Exception) -> LLMProviderError:
        types = self._sdk_error_types()

        if isinstance(exc, types.rate_limit):
            return RateLimitError(f"{self.name} rate limit: {exc}")
        if isinstance(exc, types.connection):
            return ProviderUnavailableError(f"{self.name} indisponível: {exc}")
        if isinstance(exc, types.authentication):
            return AuthenticationError(f"{self.name} autenticação falhou: {exc}")
        if isinstance(exc, types.bad_request):
            return InvalidRequestError(f"{self.name} request inválido: {exc}")
        if isinstance(exc, types.api_status):
            status_code = getattr(exc, "status_code", None)
            if status_code is not None and status_code >= 500:
                return ProviderUnavailableError(f"{self.name} erro de servidor: {exc}")
        return ProviderUnavailableError(f"{self.name} erro: {exc}")

    async def _create_completion(self, kwargs: dict[str, Any]) -> Any:
        try:
            return await self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise self._map_sdk_error(exc) from exc

    def _to_llm_response(self, response: Any) -> LLMResponse:
        text = response.choices[0].message.content or ""
        return LLMResponse(
            text=text,
            provider=self.name,
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else None,
        )

    async def _iter_stream_deltas(self, stream: Any) -> AsyncIterator[str]:
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def generate(self, request: GenerateRequest) -> LLMResponse:
        kwargs = self._build_create_kwargs(request, stream=False)
        if request.response_format is not None:
            kwargs["response_format"] = request.response_format
        response = await self._create_completion(kwargs)
        return self._to_llm_response(response)

    async def stream(self, request: StreamRequest) -> AsyncIterator[str]:
        kwargs = self._build_create_kwargs(request, stream=True)
        stream = await self._create_completion(kwargs)
        async for delta in self._iter_stream_deltas(stream):
            yield delta
