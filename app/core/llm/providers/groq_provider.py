from typing import Any

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    AuthenticationError,
    BadRequestError,
)
from groq import RateLimitError as GroqRateLimitError

from app.core.settings import settings
from app.core.llm.providers.chat_completions_adapter import (
    ChatCompletionsAdapter,
    SdkErrorTypes,
)
from app.core.llm.requests import ChatRequest

_MODEL = "openai/gpt-oss-safeguard-20b"


class GroqProvider(ChatCompletionsAdapter):
    name = "groq"
    default_model = _MODEL

    def __init__(self, client: AsyncGroq | None = None) -> None:
        super().__init__(client or AsyncGroq(api_key=settings.GROQ_API_KEY))

    def _sdk_error_types(self) -> SdkErrorTypes:
        return SdkErrorTypes(
            rate_limit=GroqRateLimitError,
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
            "max_completion_tokens": request.max_output_tokens,
            "top_p": 1,
            "stop": None,
            "stream": stream,
        }
