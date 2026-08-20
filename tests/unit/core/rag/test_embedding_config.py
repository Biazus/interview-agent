from pathlib import Path

import app.core.rag.embedding_config as embedding_config
from app.core.rag.embedding_config import EMBEDDING_MODEL_ID, VECTOR_SIZE

EXPECTED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
FORBIDDEN_BOUNDARY_TOKENS = (
    "async_messaging",
    "COLLECTION_NAME",
    "SEED_MANIFEST",
    "rag_seed",
    "rag_config",
    "domains/",
)


def test_exports_embedding_model_id_and_vector_size():
    assert EMBEDDING_MODEL_ID == EXPECTED_MODEL_ID
    assert VECTOR_SIZE == 384


def test_module_reexports_public_constants():
    assert embedding_config.EMBEDDING_MODEL_ID == EXPECTED_MODEL_ID
    assert embedding_config.VECTOR_SIZE == 384


def test_embedding_config_has_no_domain_or_collection_leaks():
    config_path = Path(embedding_config.__file__)
    source = config_path.read_text(encoding="utf-8").lower()

    for token in FORBIDDEN_BOUNDARY_TOKENS:
        assert (
            token.lower() not in source
        ), f"embedding_config must stay domain-agnostic; found forbidden token: {token!r}"
