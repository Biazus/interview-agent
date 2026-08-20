import pytest

from app.core.rag.seed_manifest import compute_manifest_hash

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


@pytest.fixture
def seed_files(tmp_path):
    first = tmp_path / "alpha.yaml"
    second = tmp_path / "beta.yaml"
    first.write_text("alpha-content", encoding="utf-8")
    second.write_text("beta-content", encoding="utf-8")
    return first, second


def test_compute_manifest_hash_is_deterministic(seed_files):
    first, second = seed_files
    files = (str(first), str(second))

    assert compute_manifest_hash(files, MODEL_ID) == compute_manifest_hash(
        files, MODEL_ID
    )


def test_compute_manifest_hash_ignores_input_file_order(seed_files):
    first, second = seed_files

    hash_forward = compute_manifest_hash((str(first), str(second)), MODEL_ID)
    hash_reverse = compute_manifest_hash((str(second), str(first)), MODEL_ID)

    assert hash_forward == hash_reverse


def test_compute_manifest_hash_changes_when_file_content_changes(seed_files):
    first, second = seed_files
    files = (str(first), str(second))
    hash_before = compute_manifest_hash(files, MODEL_ID)

    first.write_text("alpha-content-updated", encoding="utf-8")
    hash_after = compute_manifest_hash(files, MODEL_ID)

    assert hash_before != hash_after


def test_compute_manifest_hash_changes_when_model_id_changes(seed_files):
    first, second = seed_files
    files = (str(first), str(second))

    hash_a = compute_manifest_hash(files, MODEL_ID)
    hash_b = compute_manifest_hash(files, "other-model-id")

    assert hash_a != hash_b


def test_compute_manifest_hash_returns_sha256_hex(seed_files):
    first, second = seed_files
    manifest_hash = compute_manifest_hash((str(first), str(second)), MODEL_ID)

    assert isinstance(manifest_hash, str)
    assert len(manifest_hash) == 64
    assert manifest_hash.isalnum()
    assert manifest_hash == manifest_hash.lower()
