from fastembed import TextEmbedding

from app.core.rag.embedding_config import EMBEDDING_MODEL_ID

# MiniLM parity target: sentence-transformers/all-MiniLM-L6-v2


class EmbeddingProvider:
    """
    Gera embeddings localmente, sem depender de nenhuma API externa.

    Importante: este componente não faz parte da cadeia de fallback de LLM
    propositalmente. Embeddings de fontes diferentes não são
    comparáveis entre si, então precisamos de uma única fonte consistente
    para tudo que for indexado e consultado.
    """

    def __init__(self) -> None:
        self._model = TextEmbedding(model_name=EMBEDDING_MODEL_ID)

    def embed(self, text: str) -> list[float]:
        vector = next(self._model.embed([text]))
        return [float(value) for value in vector.tolist()]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [
            [float(value) for value in vector.tolist()]
            for vector in self._model.embed(texts)
        ]
