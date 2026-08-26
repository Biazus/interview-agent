from pathlib import Path

from app.core.domain.rag_config import DomainRagConfig

COLLECTION_NAME = "python_basics"
SEED_MANIFEST_FILES = ("app/domains/python_basics/rag_seed.yaml",)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SEED_YAML_PATH = _REPO_ROOT / "app/domains/python_basics/rag_seed.yaml"


def build_rag_config() -> DomainRagConfig:
    return DomainRagConfig(
        collection_name=COLLECTION_NAME,
        seed_manifest_files=SEED_MANIFEST_FILES,
        seed_yaml_path=str(_SEED_YAML_PATH),
    )
