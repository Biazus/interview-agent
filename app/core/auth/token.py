import hashlib
import secrets


def generate_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_token(raw_token)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
