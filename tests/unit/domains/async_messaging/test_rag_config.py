from pathlib import Path

from app.domains.async_messaging.rag_config import COLLECTION_NAME, SEED_MANIFEST_FILES

REPO_ROOT = Path(__file__).resolve().parents[4]
RAG_SEED_RELATIVE = Path("app/domains/async_messaging/rag_seed.yaml")


def test_collection_name_is_async_messaging():
    assert COLLECTION_NAME == "async_messaging"


def test_seed_manifest_files_is_non_empty_tuple():
    assert isinstance(SEED_MANIFEST_FILES, tuple)
    assert len(SEED_MANIFEST_FILES) >= 1


def test_seed_manifest_files_reference_existing_rag_seed():
    for path_str in SEED_MANIFEST_FILES:
        seed_path = REPO_ROOT / path_str
        assert seed_path.exists(), f"Seed manifest file missing: {path_str}"
        assert seed_path.name == "rag_seed.yaml"
        assert seed_path.samefile(REPO_ROOT / RAG_SEED_RELATIVE)
