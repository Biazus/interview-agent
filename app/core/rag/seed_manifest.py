import hashlib
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "app").is_dir():
            return candidate
    raise RuntimeError("Could not locate repository root from seed_manifest.py")


def _resolve_manifest_path(path: str, base_dir: Path) -> Path:
    manifest_path = Path(path)
    if manifest_path.is_absolute():
        return manifest_path
    return base_dir / manifest_path


def compute_manifest_hash(
    files: tuple[str, ...] | list[str],
    model_id: str,
    *,
    base_dir: Path | None = None,
) -> str:
    root = base_dir if base_dir is not None else _repo_root()
    parts: list[str] = []
    for path in sorted(files):
        resolved_path = _resolve_manifest_path(path, root)
        # Normalize CRLF so manifest hash matches git (eol=lf) on all platforms.
        file_bytes = resolved_path.read_bytes().replace(b"\r\n", b"\n")
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
