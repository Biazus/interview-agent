from unittest.mock import MagicMock, patch

import pytest

from app.core.domain.rag_config import DomainRagConfig
from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.core.rag.seed_ingestion import ingest_domain_seed
from app.core.rag.seed_manifest import compute_manifest_hash


@pytest.fixture
def vector_store() -> MagicMock:
    return MagicMock(
        spec=[
            "ensure_collection",
            "get_collection_info",
            "drop_collection",
            "upsert",
            "set_collection_metadata",
        ]
    )


@pytest.fixture
def embedder() -> MagicMock:
    mock = MagicMock(spec=["embed_batch"])
    mock.embed_batch.return_value = [[0.1, 0.2, 0.3]]
    return mock


def test_ingest_domain_seed_skips_when_manifest_matches(
    fake_test_rag_config: DomainRagConfig,
    vector_store: MagicMock,
):
    manifest_hash = compute_manifest_hash(
        fake_test_rag_config.seed_manifest_files,
        EMBEDDING_MODEL_ID,
    )
    vector_store.get_collection_info.return_value = (
        3,
        {
            "seed_manifest_hash": manifest_hash,
            "embedding_model_id": EMBEDDING_MODEL_ID,
        },
    )

    with patch(
        "app.core.rag.seed_ingestion.get_vector_store",
        return_value=vector_store,
    ):
        ingest_domain_seed(fake_test_rag_config)

    vector_store.upsert.assert_not_called()
    vector_store.drop_collection.assert_not_called()


def test_ingest_domain_seed_reseeds_when_manifest_stale(
    fake_test_rag_config: DomainRagConfig,
    vector_store: MagicMock,
    embedder: MagicMock,
):
    manifest_hash = compute_manifest_hash(
        fake_test_rag_config.seed_manifest_files,
        EMBEDDING_MODEL_ID,
    )
    vector_store.get_collection_info.return_value = (
        2,
        {
            "seed_manifest_hash": "0" * 64,
            "embedding_model_id": EMBEDDING_MODEL_ID,
        },
    )

    with (
        patch(
            "app.core.rag.seed_ingestion.get_vector_store",
            return_value=vector_store,
        ),
        patch(
            "app.core.rag.seed_ingestion.get_embedding_provider",
            return_value=embedder,
        ),
    ):
        ingest_domain_seed(fake_test_rag_config)

    vector_store.drop_collection.assert_called_once_with(
        fake_test_rag_config.collection_name
    )
    vector_store.upsert.assert_called_once()
    vector_store.set_collection_metadata.assert_called_once()
    metadata_call = vector_store.set_collection_metadata.call_args
    assert metadata_call[0][0] == fake_test_rag_config.collection_name
    metadata = metadata_call[0][1]
    assert metadata["seed_manifest_hash"] == manifest_hash
    assert metadata["embedding_model_id"] == EMBEDDING_MODEL_ID


def test_ingest_domain_seed_upserts_documents_from_yaml_path(
    fake_test_rag_config: DomainRagConfig,
    vector_store: MagicMock,
    embedder: MagicMock,
):
    vector_store.get_collection_info.return_value = (0, {})

    with (
        patch(
            "app.core.rag.seed_ingestion.get_vector_store",
            return_value=vector_store,
        ),
        patch(
            "app.core.rag.seed_ingestion.get_embedding_provider",
            return_value=embedder,
        ),
    ):
        ingest_domain_seed(fake_test_rag_config)

    vector_store.ensure_collection.assert_called_with(
        fake_test_rag_config.collection_name
    )
    embedder.embed_batch.assert_called_once_with(
        ["test document content for fake domain seed"]
    )
    upsert_args = vector_store.upsert.call_args
    assert upsert_args[0][0] == fake_test_rag_config.collection_name
    assert upsert_args[0][1] == [0]
    assert upsert_args[0][3] == [
        {
            "text": "test document content for fake domain seed",
            "topic": "dead_letter_queue",
            "source": "doc_01",
        }
    ]
