from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str  # qual provider de fato respondeu (observabilidade)
    model: str
    tokens_used: int | None = None


class LLMProvider(Protocol):
    name: str

    async def generate(self, prompt: str, **params) -> LLMResponse:
        ...

    async def stream(self, prompt: str, **params) -> AsyncIterator[str]:
        # se o provider falhar depois de já ter emitido alguns chunks (ex: conexão cai no meio),
        # esse código atual reinicia do zero no próximo provider, o que pode gerar uma resposta
        # com início duplicado ao usuário. É uma limitação conhecida e aceitável por agora
        ...