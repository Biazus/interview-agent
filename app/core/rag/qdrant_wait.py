"""Wait until Qdrant is reachable before startup or seed scripts."""

from __future__ import annotations

import logging
import os
import time

from app.core.rag.qdrant_client import create_qdrant_client

logger = logging.getLogger(__name__)


def _resolve_connection(
    host: str | None,
    port: int | None,
    api_key: str | None,
) -> tuple[str, int, str | None]:
    resolved_host = host or os.environ.get("QDRANT_HOST")
    resolved_port = port
    if resolved_port is None:
        port_str = os.environ.get("QDRANT_PORT")
        if port_str is not None:
            resolved_port = int(port_str)
    resolved_api_key = (
        api_key if api_key is not None else os.environ.get("QDRANT_API_KEY")
    )

    if resolved_host is None or resolved_port is None or resolved_api_key is None:
        from app.core.settings import settings

        if resolved_host is None:
            resolved_host = settings.QDRANT_HOST
        if resolved_port is None:
            resolved_port = settings.QDRANT_PORT
        if resolved_api_key is None:
            resolved_api_key = settings.QDRANT_API_KEY

    return resolved_host or "localhost", resolved_port or 6333, resolved_api_key


def wait_for_qdrant(
    *,
    host: str | None = None,
    port: int | None = None,
    api_key: str | None = None,
    interval_seconds: float = 2.0,
    timeout_seconds: float | None = None,
) -> None:
    resolved_host, resolved_port, resolved_api_key = _resolve_connection(
        host,
        port,
        api_key,
    )
    deadline = (
        time.monotonic() + timeout_seconds if timeout_seconds is not None else None
    )

    logger.info(
        "Waiting for Qdrant at %s:%s...",
        resolved_host,
        resolved_port,
    )
    attempt = 0
    last_warning_at = 0.0
    warning_interval_seconds = 30.0
    warning_every_n_attempts = 5

    while deadline is None or time.monotonic() < deadline:
        try:
            create_qdrant_client(
                host=resolved_host,
                port=resolved_port,
                api_key=resolved_api_key,
            ).get_collections()
            logger.info("Qdrant is ready.")
            return
        except Exception:
            attempt += 1
            now = time.monotonic()
            should_log = (
                attempt == 1
                or attempt % warning_every_n_attempts == 0
                or now - last_warning_at >= warning_interval_seconds
            )
            if should_log:
                logger.warning(
                    "Qdrant not ready at %s:%s (attempt %d)",
                    resolved_host,
                    resolved_port,
                    attempt,
                    exc_info=True,
                )
                last_warning_at = now
            time.sleep(interval_seconds)

    logger.error(
        "Qdrant not available after %ss at %s:%s",
        timeout_seconds,
        resolved_host,
        resolved_port,
    )
    raise RuntimeError(
        f"Qdrant not available at {resolved_host}:{resolved_port} after "
        f"{timeout_seconds:.0f}s"
    )
