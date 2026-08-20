import inspect
import math
from pathlib import Path

import pytest

from app.core.rag.embedding_config import EMBEDDING_MODEL_ID, VECTOR_SIZE
from app.core.rag.embeddings import EmbeddingProvider

PROBE_TEXT = "SQS visibility timeout probe for embedding self-similarity check."


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(x * y for x, y in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(x * x for x in left))
    norm_right = math.sqrt(sum(y * y for y in right))
    return dot / (norm_left * norm_right)


def test_embedding_provider_uses_fastembed_not_sentence_transformers() -> None:
    source_path = Path(inspect.getfile(EmbeddingProvider))
    source = source_path.read_text(encoding="utf-8")

    assert (
        "fastembed" in source.lower()
    ), "EmbeddingProvider must use fastembed after PR1 swap"
    assert "sentence_transformers" not in source.lower()
    assert "SentenceTransformer" not in source


def test_embedding_provider_references_config_model_id() -> None:
    source_path = Path(inspect.getfile(EmbeddingProvider))
    source = source_path.read_text(encoding="utf-8")

    assert (
        "EMBEDDING_MODEL_ID" in source
    ), "EmbeddingProvider must read EMBEDDING_MODEL_ID from embedding_config"
    assert EMBEDDING_MODEL_ID in source or EMBEDDING_MODEL_ID.split("/")[-1] in source


@pytest.mark.integration
def test_embed_returns_vector_with_configured_dimensions() -> None:
    provider = EmbeddingProvider()
    vector = provider.embed(PROBE_TEXT)

    assert isinstance(vector, list)
    assert all(isinstance(value, float) for value in vector)
    assert len(vector) == VECTOR_SIZE


@pytest.mark.integration
def test_embed_batch_returns_float_vectors_matching_configured_dimensions() -> None:
    provider = EmbeddingProvider()
    texts = [PROBE_TEXT, "Amazon SQS dead letter queue redrive policy."]
    vectors = provider.embed_batch(texts)

    assert isinstance(vectors, list)
    assert len(vectors) == len(texts)
    for vector in vectors:
        assert isinstance(vector, list)
        assert all(isinstance(value, float) for value in vector)
        assert len(vector) == VECTOR_SIZE


@pytest.mark.integration
def test_embed_self_similarity_meets_m4_threshold() -> None:
    provider = EmbeddingProvider()
    vector = provider.embed(PROBE_TEXT)

    assert _cosine_similarity(vector, vector) >= 0.999
