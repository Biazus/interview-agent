"""Run RAG seed for all registered domains."""

import importlib
import logging
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from qdrant_client import QdrantClient  # noqa: E402

import app.bootstrap  # noqa: F401, E402 — registers domains on import

from app.core.domain.registry import list_registered_domains  # noqa: E402

logger = logging.getLogger(__name__)


def _wait_for_qdrant(
    host: str | None = None,
    port: int | None = None,
    *,
    interval_seconds: float = 2.0,
    timeout_seconds: float = 120.0,
) -> None:
    resolved_host = host or os.environ.get("QDRANT_HOST", "localhost")
    resolved_port = port or int(os.environ.get("QDRANT_PORT", "6333"))
    deadline = time.monotonic() + timeout_seconds

    logger.info(
        "Waiting for Qdrant at %s:%s...",
        resolved_host,
        resolved_port,
    )
    attempt = 0
    last_warning_at = 0.0
    warning_interval_seconds = 30.0
    warning_every_n_attempts = 5

    while time.monotonic() < deadline:
        try:
            QdrantClient(host=resolved_host, port=resolved_port).get_collections()
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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    _wait_for_qdrant()

    domains = list_registered_domains()
    if not domains:
        logger.error(
            "No registered domains to seed; ensure app.bootstrap registers domains",
            extra={"reason": "empty_registry"},
        )
        sys.exit(1)

    for domain_value in domains:
        logger.info("Seeding domain: %s", domain_value)
        ingestion_module = importlib.import_module(
            f"app.domains.{domain_value}.rag_ingestion"
        )
        ingestion_module.ingest_seed_documents()


if __name__ == "__main__":
    main()
