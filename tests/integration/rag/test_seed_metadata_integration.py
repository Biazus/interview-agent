import app.bootstrap  # noqa: F401 — registers domains on import

import pytest

from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.core.rag.factory import get_vector_store
from app.core.rag.seed_ingestion import ingest_domain_seed
from app.core.rag.seed_manifest import compute_manifest_hash, manifest_matches
from app.domains.async_messaging.rag_config import (
    COLLECTION_NAME,
    SEED_MANIFEST_FILES,
    build_rag_config,
)

pytestmark = pytest.mark.integration


def test_async_messaging_seed_metadata_matches_manifest(qdrant_available: None) -> None:
    """After ingest against real Qdrant, collection metadata reflects seed manifest."""
    config = build_rag_config()
    expected_hash = compute_manifest_hash(SEED_MANIFEST_FILES, EMBEDDING_MODEL_ID)

    ingest_domain_seed(config)
    ingest_domain_seed(
        config
    )  # idempotent — must not fail when manifest already matches

    store = get_vector_store()
    points_count, metadata = store.get_collection_info(COLLECTION_NAME)

    assert points_count > 0
    assert metadata.get("seed_manifest_hash") == expected_hash
    assert metadata.get("embedding_model_id") == EMBEDDING_MODEL_ID
    assert metadata.get("seed_manifest_files") == list(SEED_MANIFEST_FILES)


def test_manifest_matches_returns_true_for_seeded_collection(
    qdrant_available: None,
) -> None:
    """manifest_matches on live metadata proves the readiness check path."""
    ingest_domain_seed(build_rag_config())

    _, metadata = get_vector_store().get_collection_info(COLLECTION_NAME)

    assert manifest_matches(metadata, SEED_MANIFEST_FILES, EMBEDDING_MODEL_ID)
