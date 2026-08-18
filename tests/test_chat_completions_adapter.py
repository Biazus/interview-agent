from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.llm.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.core.llm.providers.chat_completions_adapter import (
    ChatCompletionsAdapter,
    SdkErrorTypes,
)
from app.core.llm.requests import GenerateRequest, StreamRequest


class _FakeRateLimitError(Exception):
    pass


class _FakeConnectionError(Exception):
    pass


class _FakeAuthError(Exception):
    pass


class _FakeBadRequestError(Exception):
    pass


class _FakeAPIStatusError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class _FakeAdapter(ChatCompletionsAdapter):
    name = "fake"
    default_model = "fake-model"

    def _sdk_error_types(self) -> SdkErrorTypes:
        return SdkErrorTypes(
            rate_limit=_FakeRateLimitError,
            connection=(_FakeConnectionError,),
            authentication=_FakeAuthError,
            bad_request=_FakeBadRequestError,
            api_status=_FakeAPIStatusError,
        )

    def _build_create_kwargs(self, request, stream: bool) -> dict:
        return {
            "messages": self._build_messages(request),
            "model": request.model or self.default_model,
            "temperature": request.temperature,
            "stream": stream,
        }


@pytest.mark.asyncio
async def test_generate_returns_llm_response():
    client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "hello"
    fake_response.model = "fake-model"
    fake_response.usage.total_tokens = 10
    client.chat.completions.create = AsyncMock(return_value=fake_response)

    adapter = _FakeAdapter(client)
    result = await adapter.generate(GenerateRequest.simple("hi"))

    assert result.text == "hello"
    assert result.provider == "fake"
    assert result.tokens_used == 10
    client.chat.completions.create.assert_awaited_once()
    call_kwargs = client.chat.completions.create.await_args.kwargs
    assert call_kwargs["messages"][0]["content"] == "You are a helpful assistant."
    assert call_kwargs["messages"][1]["content"] == "hi"


@pytest.mark.asyncio
async def test_generate_passes_response_format():
    client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "{}"
    fake_response.model = "fake-model"
    fake_response.usage = None
    client.chat.completions.create = AsyncMock(return_value=fake_response)

    adapter = _FakeAdapter(client)
    fmt = {"type": "json_object"}
    await adapter.generate(GenerateRequest(prompt="p", response_format=fmt))

    assert client.chat.completions.create.await_args.kwargs["response_format"] == fmt


@pytest.mark.asyncio
async def test_stream_yields_deltas():
    chunk1 = MagicMock()
    chunk1.choices[0].delta.content = "hel"
    chunk2 = MagicMock()
    chunk2.choices[0].delta.content = "lo"
    chunk3 = MagicMock()
    chunk3.choices[0].delta.content = None

    async def fake_stream():
        for c in [chunk1, chunk2, chunk3]:
            yield c

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=fake_stream())

    adapter = _FakeAdapter(client)
    chunks = [c async for c in adapter.stream(StreamRequest(prompt="hi"))]

    assert chunks == ["hel", "lo"]


def test_map_sdk_error_rate_limit():
    adapter = _FakeAdapter(MagicMock())
    mapped = adapter._map_sdk_error(_FakeRateLimitError("limit"))
    assert isinstance(mapped, RateLimitError)


def test_map_sdk_error_connection():
    adapter = _FakeAdapter(MagicMock())
    mapped = adapter._map_sdk_error(_FakeConnectionError("down"))
    assert isinstance(mapped, ProviderUnavailableError)


def test_map_sdk_error_authentication():
    adapter = _FakeAdapter(MagicMock())
    mapped = adapter._map_sdk_error(_FakeAuthError("401"))
    assert isinstance(mapped, AuthenticationError)


def test_map_sdk_error_bad_request():
    adapter = _FakeAdapter(MagicMock())
    mapped = adapter._map_sdk_error(_FakeBadRequestError("400"))
    assert isinstance(mapped, InvalidRequestError)


def test_map_sdk_error_server_status():
    adapter = _FakeAdapter(MagicMock())
    mapped = adapter._map_sdk_error(_FakeAPIStatusError("500", status_code=500))
    assert isinstance(mapped, ProviderUnavailableError)


@pytest.mark.asyncio
async def test_create_completion_translates_sdk_errors():
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=_FakeRateLimitError("limit"))
    adapter = _FakeAdapter(client)

    with pytest.raises(RateLimitError):
        await adapter.generate(GenerateRequest.simple("hi"))
