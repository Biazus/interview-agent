"""Tipos de request para chamadas LLM — normalizam params entre providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_SYSTEM_PROMPT = "You are an interviewer assistant."
DEFAULT_MAX_OUTPUT_TOKENS = 1024


@dataclass(frozen=True)
class ChatRequest:
    prompt: str
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.5
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    model: str | None = None


@dataclass(frozen=True)
class GenerateRequest(ChatRequest):
    response_format: dict[str, Any] | None = None

    @staticmethod
    def simple(prompt: str) -> GenerateRequest:
        return GenerateRequest(prompt=prompt)


@dataclass(frozen=True)
class StreamRequest(ChatRequest):
    pass
