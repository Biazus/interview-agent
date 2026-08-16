from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingProvider:
    """
    Gera embeddings localmente, sem depender de nenhuma API externa.

    Importante: este componente não faz parte da cadeia de fallback de LLM
    propositalmente. Embeddings de fontes diferentes não são
    comparáveis entre si, então precisamos de uma única fonte consistente
    para tudo que for indexado e consultado.
    """

    def __init__(self) -> None:
        self._model = SentenceTransformer(_MODEL_NAME)

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts).tolist()
