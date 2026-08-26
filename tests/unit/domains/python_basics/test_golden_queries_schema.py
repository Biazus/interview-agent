from collections import Counter
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
GOLDEN_QUERIES_PATH = REPO_ROOT / "app/domains/python_basics/golden_queries.yaml"
RAG_SEED_PATH = REPO_ROOT / "app/domains/python_basics/rag_seed.yaml"

EXPECTED_TOPICS = frozenset(
    {
        "data_types",
        "variables_scope",
        "control_flow",
        "functions",
        "collections",
        "comprehensions",
        "exceptions",
        "classes_basics",
        "modules_imports",
        "file_io",
    }
)
PLACEHOLDER_VALUES = frozenset({"", "todo", "tbd", "fixme", "placeholder", "changeme"})
REQUIRED_QUERY_FIELDS = frozenset({"id", "query", "topic", "expected_top1_source"})


@pytest.fixture(scope="module")
def golden_queries_document():
    if not GOLDEN_QUERIES_PATH.exists():
        pytest.fail(
            f"PR0 deliverable missing: {GOLDEN_QUERIES_PATH.relative_to(REPO_ROOT)}",
            pytrace=False,
        )
    with GOLDEN_QUERIES_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.fixture(scope="module")
def rag_seed_doc_ids():
    with RAG_SEED_PATH.open(encoding="utf-8") as handle:
        seed_data = yaml.safe_load(handle)
    return {doc["id"] for doc in seed_data["documents"]}


def test_golden_queries_top_level_schema(golden_queries_document):
    assert golden_queries_document["version"] == 1
    assert golden_queries_document["domain"] == "python_basics"
    assert golden_queries_document["collection"] == "python_basics"
    assert isinstance(golden_queries_document["queries"], list)


def test_golden_queries_has_twenty_entries(golden_queries_document):
    assert len(golden_queries_document["queries"]) == 20


def test_golden_queries_has_two_queries_per_topic(golden_queries_document):
    topic_counts = Counter(
        query["topic"] for query in golden_queries_document["queries"]
    )

    assert set(topic_counts) == EXPECTED_TOPICS
    for topic in EXPECTED_TOPICS:
        assert topic_counts[topic] == 2


def test_each_golden_query_has_required_fields(golden_queries_document):
    query_ids: set[str] = set()

    for query in golden_queries_document["queries"]:
        assert REQUIRED_QUERY_FIELDS.issubset(query.keys())

        assert isinstance(query["id"], str) and query["id"].strip()
        assert isinstance(query["query"], str) and query["query"].strip()
        assert query["topic"] in EXPECTED_TOPICS

        expected_source = query["expected_top1_source"]
        assert isinstance(expected_source, str)
        assert expected_source.strip()
        assert expected_source.strip().lower() not in PLACEHOLDER_VALUES

        assert query["id"] not in query_ids
        query_ids.add(query["id"])


def test_expected_top1_source_exists_in_rag_seed(
    golden_queries_document,
    rag_seed_doc_ids,
):
    for query in golden_queries_document["queries"]:
        expected_source = query["expected_top1_source"]
        assert (
            expected_source in rag_seed_doc_ids
        ), f"Query {query['id']!r} references unknown seed doc {expected_source!r}"
