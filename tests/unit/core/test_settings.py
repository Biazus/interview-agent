import pytest

pytest.importorskip("app.core.settings", reason="Fase 0 pendente: app.core.settings")

from app.core.settings import Settings  # noqa: E402


def test_settings_loads_database_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@localhost:5432/db",
    )
    monkeypatch.setenv("GROQ_API_KEY", "groq-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-test")

    settings = Settings()

    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"


def test_settings_auth_token_ttl_defaults_to_86400(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-test")
    monkeypatch.delenv("AUTH_TOKEN_TTL_SECONDS", raising=False)

    settings = Settings()

    assert settings.AUTH_TOKEN_TTL_SECONDS == 86400


def test_settings_loads_llm_secrets(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("GROQ_API_KEY", "secret-groq")
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-openrouter")

    settings = Settings()

    assert settings.GROQ_API_KEY == "secret-groq"
    assert settings.OPENROUTER_API_KEY == "secret-openrouter"
