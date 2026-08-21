import logging

from app.core.exceptions import RagNotReady
from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.core.rag.factory import get_vector_store
from app.core.rag.seed_manifest import manifest_matches
from app.core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


def check_rag_ready(
    collection_name: str,
    manifest_files: tuple[str, ...],
    *,
    vector_store: VectorStore | None = None,
    model_id: str = EMBEDDING_MODEL_ID,
) -> None:
    """Raises RagNotReady if collection empty or manifest stale."""
    store = vector_store or get_vector_store()

    try:
        points_count, metadata = store.get_collection_info(collection_name)
    except Exception:
        logger.warning(
            "RAG not ready: Qdrant unavailable",
            extra={"reason": "qdrant_unavailable", "collection_name": collection_name},
            exc_info=True,
        )
        raise RagNotReady() from None

    if points_count == 0:
        logger.warning(
            "RAG not ready: collection empty",
            extra={"reason": "empty_collection", "collection_name": collection_name},
        )
        raise RagNotReady()

    if not manifest_matches(metadata, manifest_files, model_id):
        logger.warning(
            "RAG not ready: manifest stale",
            extra={"reason": "stale_manifest", "collection_name": collection_name},
        )
        raise RagNotReady()
