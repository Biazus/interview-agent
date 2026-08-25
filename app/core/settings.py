from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://interview:interview@localhost:5432/interview_agent"
)

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class Settings(BaseSettings):
    DATABASE_URL: str = _DEFAULT_DATABASE_URL
    AUTH_TOKEN_TTL_SECONDS: int = 86400
    LOG_LEVEL: str = "INFO"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    CORS_ORIGINS: list[str] = _DEFAULT_CORS_ORIGINS
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
