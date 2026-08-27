from pathlib import Path

from app.core.domain.rag_config import DomainRagConfig
from app.domains.python_basics.rag_config import (
    COLLECTION_NAME,
    SEED_MANIFEST_FILES,
    build_rag_config,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
RAG_SEED_RELATIVE = Path("app/domains/python_basics/rag_seed.yaml")


def test_build_rag_config():
    config = build_rag_config()

    assert isinstance(config, DomainRagConfig)
    assert config.collection_name == COLLECTION_NAME
    assert config.seed_manifest_files == SEED_MANIFEST_FILES
    assert Path(config.seed_yaml_path).samefile(REPO_ROOT / RAG_SEED_RELATIVE)
