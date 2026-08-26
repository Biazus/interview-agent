"""Run RAG seed for all registered domains."""

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import app.bootstrap  # noqa: F401, E402 — registers domains on import

from app.core.domain.registry import (  # noqa: E402
    DomainEnum,
    get_domain_rag_config,
    list_registered_domains,
)
from app.core.rag.qdrant_wait import wait_for_qdrant  # noqa: E402
from app.core.rag.seed_ingestion import ingest_domain_seed  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    wait_for_qdrant(timeout_seconds=120.0)

    domains = list_registered_domains()
    if not domains:
        logger.error(
            "No registered domains to seed; ensure app.bootstrap registers domains",
            extra={"reason": "empty_registry"},
        )
        sys.exit(1)

    for domain_value in domains:
        logger.info("Seeding domain: %s", domain_value)
        config = get_domain_rag_config(DomainEnum(domain_value))
        ingest_domain_seed(config)


if __name__ == "__main__":
    main()
