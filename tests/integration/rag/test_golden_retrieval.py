from pathlib import Path

import pytest
import yaml

from app.core.rag.qdrant_retriever import QdrantRetriever

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_QUERIES_PATH = REPO_ROOT / "app/domains/async_messaging/golden_queries.yaml"


def _load_golden_query_cases() -> list[tuple[str, str, str, str]]:
    with GOLDEN_QUERIES_PATH.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    queries = document["queries"]
    assert len(queries) == 8

    return [
        (
            query["id"],
            query["query"].strip(),
            query["topic"],
            query["expected_top1_source"],
        )
        for query in queries
    ]


GOLDEN_QUERY_CASES = _load_golden_query_cases()


@pytest.mark.parametrize(
    ("query_id", "query_text", "topic", "expected_top1_source"),
    GOLDEN_QUERY_CASES,
    ids=[case[0] for case in GOLDEN_QUERY_CASES],
)
def test_golden_query_top1_matches_expected_source(
    async_messaging_retriever: QdrantRetriever,
    query_id: str,
    query_text: str,
    topic: str,
    expected_top1_source: str,
) -> None:
    chunks = async_messaging_retriever.retrieve(
        query=query_text,
        top_k=1,
        topic=topic,
    )

    assert (
        len(chunks) == 1
    ), f"{query_id}: expected exactly one chunk, got {len(chunks)}"
    top_chunk = chunks[0]
    assert top_chunk.source == expected_top1_source, (
        f"{query_id}: expected top-1 source {expected_top1_source!r}, "
        f"got {top_chunk.source!r} (score={top_chunk.score})"
    )
