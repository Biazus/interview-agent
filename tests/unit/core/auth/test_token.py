import re

import pytest

pytest.importorskip("app.core.auth.token", reason="Fase 1 pendente: app.core.auth")

from app.core.auth.token import generate_token, hash_token  # noqa: E402


def test_generate_token_returns_opaque_token_and_hash():
    raw_token, token_hash = generate_token()

    assert len(raw_token) >= 32
    assert token_hash == hash_token(raw_token)
    assert raw_token != token_hash


def test_hash_token_is_sha256_hex():
    raw = "opaque-token-value"
    token_hash = hash_token(raw)

    assert re.fullmatch(r"[0-9a-f]{64}", token_hash)


def test_hash_token_is_deterministic():
    raw = "same-token"

    assert hash_token(raw) == hash_token(raw)
