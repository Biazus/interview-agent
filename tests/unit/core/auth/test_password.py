import pytest

pytest.importorskip("app.core.auth.password", reason="Fase 1 pendente: app.core.auth")

from app.core.auth.password import hash_password, verify_password  # noqa: E402


def test_hash_password_returns_argon2_hash():
    hashed = hash_password("senha-segura-123")

    assert hashed != "senha-segura-123"
    assert hashed.startswith("$argon2")


def test_verify_password_accepts_correct_password():
    password = "minha-senha-forte"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("senha-correta")

    assert verify_password("senha-errada", hashed) is False
