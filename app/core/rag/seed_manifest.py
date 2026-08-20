import hashlib
from pathlib import Path


def compute_manifest_hash(files: tuple[str, ...] | list[str], model_id: str) -> str:
    parts: list[str] = []
    for path in sorted(files):
        file_bytes = Path(path).read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        parts.append(f"{path}:{file_hash}")
    parts.append(f"model:{model_id}")
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return digest


def manifest_matches(
    stored_metadata: dict,
    files: tuple[str, ...] | list[str],
    model_id: str,
) -> bool:
    if not stored_metadata:
        return False

    stored_hash = stored_metadata.get("seed_manifest_hash")
    stored_model_id = stored_metadata.get("embedding_model_id")
    if not stored_hash or not stored_model_id:
        return False

    if stored_model_id != model_id:
        return False

    # compute_manifest_hash already hashes file contents and model_id.
    expected_hash = compute_manifest_hash(files, model_id)
    return stored_hash == expected_hash
