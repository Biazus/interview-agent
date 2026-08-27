from pathlib import Path

from app.domains.python_basics.rag_config import COLLECTION_NAME, SEED_MANIFEST_FILES

REPO_ROOT = Path(__file__).resolve().parents[4]
RAG_SEED_RELATIVE = Path("app/domains/python_basics/rag_seed.yaml")


def test_collection_name_is_python_basics():
    assert COLLECTION_NAME == "python_basics"


def test_seed_manifest_files_point_to_python_basics_rag_seed():
    assert SEED_MANIFEST_FILES == ("app/domains/python_basics/rag_seed.yaml",)
    assert (REPO_ROOT / RAG_SEED_RELATIVE).is_file()
