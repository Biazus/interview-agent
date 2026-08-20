from typing import Protocol
from uuid import UUID


class TokenValidator(Protocol):
    async def validate(self, raw_token: str) -> UUID | None: ...
