from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
)
from openai import RateLimitError as OpenAIRateLimitError

from app.core.llm.config import settings
from app.core.llm.providers.chat_completions_adapter import (
    ChatCompletionsAdapter,
    SdkErrorTypes,
)
from app.core.llm.requests import ChatRequest

_MODEL = "nvidia/nemotron-3.5-lightning:free"
_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(ChatCompletionsAdapter):
    name = "openrouter"
    default_model = _MODEL

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        super().__init__(
            client
            or AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=_BASE_URL,
            )
        )

    def _sdk_error_types(self) -> SdkErrorTypes:
        return SdkErrorTypes(
            rate_limit=OpenAIRateLimitError,
            connection=(APIConnectionError, APITimeoutError),
            authentication=AuthenticationError,
            bad_request=BadRequestError,
            api_status=APIStatusError,
        )

    def _build_create_kwargs(
        self, request: ChatRequest, stream: bool
    ) -> dict[str, Any]:
        return {
            "messages": self._build_messages(request),
            "model": request.model or self.default_model,
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "stream": stream,
        }
