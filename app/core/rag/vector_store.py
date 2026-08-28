from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.rag.embedding_config import VECTOR_SIZE
from app.core.rag.qdrant_client import create_qdrant_client


class VectorStore:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: str | None = None,
    ) -> None:
        self._client = create_qdrant_client(host=host, port=port, api_key=api_key)

    def ensure_collection(self, collection_name: str) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if collection_name not in existing:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

    def get_collection_info(self, collection_name: str) -> tuple[int, dict]:
        if not self._client.collection_exists(collection_name):
            return (0, {})
        info = self._client.get_collection(collection_name)
        points_count = info.points_count or 0
        metadata = info.config.metadata if info.config else None
        if metadata is None:
            return (points_count, {})
        return (points_count, dict(metadata))

    def set_collection_metadata(self, collection_name: str, metadata: dict) -> None:
        self._client.update_collection(
            collection_name=collection_name,
            metadata=metadata,
        )

    def drop_collection(self, collection_name: str) -> None:
        self._client.delete_collection(collection_name=collection_name)

    def upsert(
        self,
        collection_name: str,
        ids: list[int],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        points = [
            PointStruct(id=idx, vector=vector, payload=payload)
            for idx, vector, payload in zip(ids, vectors, payloads)
        ]
        self._client.upsert(collection_name=collection_name, points=points)

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 3,
        topic: str | None = None,
    ) -> list[dict]:
        query_filter = None
        if topic is not None:
            query_filter = Filter(
                must=[FieldCondition(key="topic", match=MatchValue(value=topic))]
            )

        results = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
        )
        return [{"score": r.score, **r.payload} for r in results.points]
