from pathlib import Path

import yaml

from app.core.rag.embeddings import EmbeddingProvider
from app.core.rag.vector_store import VectorStore

_COLLECTION_NAME = "async_messaging"
_SEED_PATH = Path(__file__).parent / "rag_seed.yaml"


def ingest_seed_documents() -> None:
    with open(_SEED_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    documents = data["documents"]
    embedder = EmbeddingProvider()
    store = VectorStore()

    store.ensure_collection(_COLLECTION_NAME)

    texts = [doc["text"] for doc in documents]
    vectors = embedder.embed_batch(texts)

    ids = list(range(len(documents)))
    payloads = [
        {"text": doc["text"], "topic": doc["topic"], "source": doc["id"]}
        for doc in documents
    ]

    store.upsert(_COLLECTION_NAME, ids, vectors, payloads)
    print(f"{len(documents)} documentos indexados na coleção '{_COLLECTION_NAME}'.")
