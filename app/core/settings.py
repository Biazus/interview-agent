from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://interview:interview@localhost:5432/interview_agent"
)


class Settings(BaseSettings):
    DATABASE_URL: str = _DEFAULT_DATABASE_URL
    AUTH_TOKEN_TTL_SECONDS: int = 86400
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
