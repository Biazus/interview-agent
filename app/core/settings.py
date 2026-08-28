from typing import Any

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://interview:interview@localhost:5432/interview_agent"
)

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

_DEFAULT_CORS_ORIGINS_STR = ",".join(_DEFAULT_CORS_ORIGINS)


class Settings(BaseSettings):
    DATABASE_URL: str = _DEFAULT_DATABASE_URL
    AUTH_TOKEN_TTL_SECONDS: int = 86400
    LOG_LEVEL: str = "INFO"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None
    CORS_ORIGINS: str = _DEFAULT_CORS_ORIGINS_STR
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _normalize_cors_origins(cls, value: Any) -> str:
        if value is None:
            return _DEFAULT_CORS_ORIGINS_STR
        if isinstance(value, list):
            return ",".join(
                str(origin).strip() for origin in value if str(origin).strip()
            )
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return _DEFAULT_CORS_ORIGINS_STR
            return stripped
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
