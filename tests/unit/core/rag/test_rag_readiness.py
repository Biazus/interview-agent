from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import RagNotReady
from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.core.rag.rag_readiness import check_rag_ready
from app.core.rag.seed_manifest import compute_manifest_hash
from app.domains.async_messaging import rag_config

COLLECTION_NAME = rag_config.COLLECTION_NAME
MANIFEST_FILES = rag_config.SEED_MANIFEST_FILES


def _expected_manifest_hash() -> str:
    return compute_manifest_hash(MANIFEST_FILES, EMBEDDING_MODEL_ID)


def _ready_metadata() -> dict:
    return {
        "seed_manifest_hash": _expected_manifest_hash(),
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "seed_manifest_files": list(MANIFEST_FILES),
        "seeded_at": "2026-01-01T00:00:00Z",
    }


@pytest.fixture
def vector_store() -> MagicMock:
    return MagicMock(spec=["get_collection_info"])


def test_check_rag_ready_passes_when_collection_seeded_and_manifest_matches(
    vector_store: MagicMock,
):
    vector_store.get_collection_info.return_value = (42, _ready_metadata())

    check_rag_ready(COLLECTION_NAME, MANIFEST_FILES, vector_store=vector_store)

    vector_store.get_collection_info.assert_called_once_with(COLLECTION_NAME)


def test_check_rag_ready_raises_when_collection_empty(vector_store: MagicMock):
    vector_store.get_collection_info.return_value = (0, {})

    with pytest.raises(RagNotReady):
        check_rag_ready(COLLECTION_NAME, MANIFEST_FILES, vector_store=vector_store)


def test_check_rag_ready_raises_when_metadata_missing(vector_store: MagicMock):
    vector_store.get_collection_info.return_value = (10, {})

    with pytest.raises(RagNotReady):
        check_rag_ready(COLLECTION_NAME, MANIFEST_FILES, vector_store=vector_store)


def test_check_rag_ready_raises_when_manifest_stale(vector_store: MagicMock):
    stale_metadata = _ready_metadata()
    stale_metadata["seed_manifest_hash"] = "0" * 64
    vector_store.get_collection_info.return_value = (10, stale_metadata)

    with pytest.raises(RagNotReady):
        check_rag_ready(COLLECTION_NAME, MANIFEST_FILES, vector_store=vector_store)


def test_check_rag_ready_raises_when_embedding_model_id_mismatch(
    vector_store: MagicMock,
):
    mismatched_metadata = _ready_metadata()
    mismatched_metadata["embedding_model_id"] = "other-model-id"
    vector_store.get_collection_info.return_value = (10, mismatched_metadata)

    with pytest.raises(RagNotReady):
        check_rag_ready(COLLECTION_NAME, MANIFEST_FILES, vector_store=vector_store)


def test_check_rag_ready_raises_when_qdrant_unavailable(vector_store: MagicMock):
    vector_store.get_collection_info.side_effect = ConnectionError("connection refused")

    with pytest.raises(RagNotReady):
        check_rag_ready(COLLECTION_NAME, MANIFEST_FILES, vector_store=vector_store)


def test_check_rag_ready_default_uses_get_vector_store_factory():
    mock_store = MagicMock(spec=["get_collection_info"])
    mock_store.get_collection_info.return_value = (42, _ready_metadata())

    with patch(
        "app.core.rag.rag_readiness.get_vector_store", return_value=mock_store
    ) as mock_factory:
        check_rag_ready(COLLECTION_NAME, MANIFEST_FILES)

    mock_factory.assert_called_once()
    mock_store.get_collection_info.assert_called_once_with(COLLECTION_NAME)


def test_check_rag_ready_default_uses_settings_host():
    from app.core.rag.factory import clear_rag_cache, get_vector_store

    captured: list[tuple[str, int]] = []

    def capture_vector_store(host: str, port: int) -> MagicMock:
        captured.append((host, port))
        return MagicMock(spec=["get_collection_info"])

    with (
        patch("app.core.rag.factory.settings") as mock_settings,
        patch(
            "app.core.rag.factory.VectorStore",
            side_effect=capture_vector_store,
        ),
    ):
        clear_rag_cache()
        mock_settings.QDRANT_HOST = "vector-db"
        mock_settings.QDRANT_PORT = 6333

        get_vector_store()

    assert captured == [("vector-db", 6333)]


def test_check_rag_ready_uses_only_vector_store_abstraction():
    import app.core.rag.rag_readiness as rag_readiness_module

    source = Path(rag_readiness_module.__file__).read_text(encoding="utf-8")

    assert "QdrantClient" not in source
    assert "app.domains" not in source
    assert "rag_config" not in source
