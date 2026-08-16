from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

_VECTOR_SIZE = 384  # dimensão de saída do all-MiniLM-L6-v2


class VectorStore:
    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self._client = QdrantClient(host=host, port=port)

    def ensure_collection(self, collection_name: str) -> None:
        """Cria a coleção se ainda não existir (idempotente)."""
        existing = [c.name for c in self._client.get_collections().collections]
        if collection_name not in existing:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=_VECTOR_SIZE, distance=Distance.COSINE
                ),
            )

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        points = [
            PointStruct(id=idx, vector=vector, payload=payload)
            for idx, (vector, payload) in enumerate(zip(vectors, payloads))
        ]
        self._client.upsert(collection_name=collection_name, points=points)

    def search(
        self, collection_name: str, query_vector: list[float], top_k: int = 3
    ) -> list[dict]:
        results = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
        )
        return [{"score": r.score, **r.payload} for r in results.points]
