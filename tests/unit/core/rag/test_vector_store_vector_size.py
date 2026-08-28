from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.rag.embedding_config import VECTOR_SIZE
from app.core.rag.vector_store import VectorStore


def test_vector_store_module_imports_vector_size_from_embedding_config() -> None:
    from app.core.rag import vector_store

    source = Path(vector_store.__file__).read_text(encoding="utf-8")

    assert (
        "from app.core.rag.embedding_config import VECTOR_SIZE" in source
    ), "vector_store must import VECTOR_SIZE from embedding_config (PR1)"
    assert (
        "_VECTOR_SIZE" not in source
    ), "vector_store must not define a local _VECTOR_SIZE constant (PR1)"


def test_ensure_collection_uses_vector_size_from_embedding_config() -> None:
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    with patch(
        "app.core.rag.vector_store.create_qdrant_client",
        return_value=mock_client,
    ):
        store = VectorStore()
        store.ensure_collection("test_collection")

    mock_client.create_collection.assert_called_once()
    vectors_config = mock_client.create_collection.call_args.kwargs["vectors_config"]
    assert vectors_config.size == VECTOR_SIZE == 384
