# RAG migration — PR0 fastembed parity benchmark

> **Archived** — PR0 GO/NO-GO gate completed (**GO**: M1 7/8, M2 100%, M3 384, M4 1.0).
> The validation script `scripts/benchmark_embedding_parity.py` was removed after the
> decision; ongoing checks move to PR1 golden retrieval CI (`test_golden_retrieval.py`).

This document describes how the PR0 GO/NO-GO benchmark worked before swapping
the production embedder from SentenceTransformer to fastembed (PR1).

## Prerequisites (historical)

```bash
uv sync --group dev
```

The benchmark used:

- **SentenceTransformer** (current production stack) via runtime deps
- **fastembed** (candidate embedder) via the `dev` dependency group only

Production code (`app/core/rag/embeddings.py`) was **not** changed in PR0.

## Run the benchmark (removed)

Previously run from the repository root:

```bash
uv run python scripts/benchmark_embedding_parity.py --verbose
```

Without `--verbose`, the script printed only the final verdict. **This script no
longer exists in the repo.**

## GO / NO-GO criteria

Exit code **0** = GO (proceed to PR1). Exit code **1** = NO-GO.

All four metrics had to pass:

| ID | Metric | Threshold | Meaning |
|----|--------|-----------|---------|
| M1 | `m1_top1_matches` | ≥ **6 / 8** | Golden queries where SentenceTransformer and fastembed agree on top-1 doc ID |
| M2 | `m2_top3_overlap_pct` | ≥ **80%** | Share of queries whose `expected_top1_source` appears in fastembed top-3 |
| M3 | `m3_vector_dims` | **384** | fastembed output dimension matches MiniLM parity target |
| M4 | `m4_self_similarity` | ≥ **0.999** | `cosine(embed(t), embed(t))` for a probe string |

The script loaded seed documents from `app/domains/async_messaging/rag_seed.yaml`
and golden queries from `app/domains/async_messaging/golden_queries.yaml`,
then performed in-memory cosine search (no Qdrant required for PR0).

## Interpreting results

### M1 — top-1 agreement

High M1 means both embedders rank the same document first for most queries.
PR0 required at least 6/8; PR1 CI requires **8/8** golden top-1 matches.

### M2 — expected source in top-3

Validates that `expected_top1_source` values in `golden_queries.yaml` are
semantically aligned with fastembed retrieval.

### M3 — dimensions

Must be exactly 384 for MiniLM-parity model
`sentence-transformers/all-MiniLM-L6-v2`.

### M4 — self-similarity

Sanity check that the embedder returns stable, normalized vectors.
Values below 0.999 suggest a broken or incompatible model configuration.

## Config SSOT (PR0)

| Module | Constants |
|--------|-----------|
| `app/core/rag/embedding_config.py` | `EMBEDDING_MODEL_ID`, `VECTOR_SIZE` |
| `app/domains/async_messaging/rag_config.py` | `COLLECTION_NAME`, `SEED_MANIFEST_FILES` |

## Outcome

- **GO** — proceed to PR1 (fastembed production swap + golden CI)
- **NO-GO** — investigate model mismatch, golden query wording, or seed content;
  do not proceed to PR1 until M1–M4 pass
