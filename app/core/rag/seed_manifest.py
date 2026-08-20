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
