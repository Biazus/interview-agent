import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml

from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.core.rag.factory import get_embedding_provider, get_vector_store
from app.core.rag.seed_manifest import compute_manifest_hash, manifest_matches
from app.domains.async_messaging import rag_config

logger = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).parent / "rag_seed.yaml"


def _load_seed_documents() -> list[dict]:
    with open(_SEED_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["documents"]


def _seed_collection(store, collection_name: str) -> int:
    documents = _load_seed_documents()
    embedder = get_embedding_provider()
    texts = [doc["text"] for doc in documents]
    vectors = embedder.embed_batch(texts)
    ids = list(range(len(documents)))
    payloads = [
        {"text": doc["text"], "topic": doc["topic"], "source": doc["id"]}
        for doc in documents
    ]
    store.upsert(collection_name, ids, vectors, payloads)
    return len(documents)


def ingest_seed_documents() -> None:
    collection_name = rag_config.COLLECTION_NAME
    manifest_files = rag_config.SEED_MANIFEST_FILES
    store = get_vector_store()

    store.ensure_collection(collection_name)
    points_count, metadata = store.get_collection_info(collection_name)

    if points_count > 0 and manifest_matches(
        metadata, manifest_files, EMBEDDING_MODEL_ID
    ):
        logger.info(
            "Seed skipped: collection '%s' manifest matches",
            collection_name,
        )
        return

    if points_count > 0:
        logger.info(
            "Reseeding collection '%s': manifest stale",
            collection_name,
            extra={"reason": "stale_manifest"},
        )
        store.drop_collection(collection_name)

    store.ensure_collection(collection_name)
    document_count = _seed_collection(store, collection_name)

    store.set_collection_metadata(
        collection_name,
        {
            "seed_manifest_hash": compute_manifest_hash(
                manifest_files, EMBEDDING_MODEL_ID
            ),
            "embedding_model_id": EMBEDDING_MODEL_ID,
            "seed_manifest_files": list(manifest_files),
            "seeded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
    logger.info(
        "Indexed %d documents in collection '%s'.",
        document_count,
        collection_name,
    )
