"""Factory for Qdrant client connections (local Docker vs Qdrant Cloud)."""

from __future__ import annotations

from qdrant_client import QdrantClient


def create_qdrant_client(
    *,
    host: str = "localhost",
    port: int = 6333,
    api_key: str | None = None,
) -> QdrantClient:
    if api_key:
        return QdrantClient(host=host, port=port, https=True, api_key=api_key)
    return QdrantClient(host=host, port=port)
