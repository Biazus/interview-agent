import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml

from app.core.domain.rag_config import DomainRagConfig
from app.core.rag.embedding_config import EMBEDDING_MODEL_ID
from app.core.rag.factory import get_embedding_provider, get_vector_store
from app.core.rag.seed_manifest import compute_manifest_hash, manifest_matches

logger = logging.getLogger(__name__)


def _load_seed_documents(seed_yaml_path: str) -> list[dict]:
    with open(Path(seed_yaml_path), encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["documents"]


def _seed_collection(store, collection_name: str, seed_yaml_path: str) -> int:
    documents = _load_seed_documents(seed_yaml_path)
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


def ingest_domain_seed(config: DomainRagConfig) -> None:
    collection_name = config.collection_name
    manifest_files = config.seed_manifest_files
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
    document_count = _seed_collection(store, collection_name, config.seed_yaml_path)

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
