# Current Plan — v0.2 Deploy Hardening (fastembed + seed híbrido)

**Status:** PR0 done · **PR1 done** · **PR2 done** · **PR3:** next  
**Last updated:** August 2026  
**Owner decisions:** Miller  

Single source of truth for agents (`revisor-arquitetural`, `escritor-testes`, `executor-codigo`, etc.) and for restarting chat context.

Related docs: [`technical_roadmap.md`](./technical_roadmap.md) · [`product_roadmap.md`](./product_roadmap.md) · [`todo.md`](./todo.md)

---

## Problem statement

| Metric | Baseline (Aug 2026) | Target (v0.2) |
|--------|---------------------|---------------|
| Docker image | **8.54 GB** (`interview-agent-api:latest`) | **≤ 650 MB** (CI hard gate; aspirational ~200–400 MB) |
| Cold start | ~1 min | Seconds–tens of seconds (after seed skip on restart) |
| Root cause | `sentence-transformers` → torch 2.13 + CUDA/NVIDIA stack in CPU-only container | Remove torch; use **fastembed** (ONNX) |
| Seed | `ingest_seed_documents()` on **every** API boot | Decoupled init job + manifest hash *(PR2 ✅)* |
| RAG failure mode | Empty retrieval → LLM evaluates without context (silent) | **`RAG_NOT_READY` (503)** on `start_interview` *(PR2 ✅)* |

---

## Combination X — decisions locked

| Dimension | Choice | Rejected alternatives |
|-----------|--------|----------------------|
| **Embedding stack** | **fastembed in-process** (ONNX), remove `sentence-transformers` / `torch` | Torch CPU-only (~1–1.5 GB); sidecar; hosted API |
| **Model** | **MiniLM-parity** — `sentence-transformers/all-MiniLM-L6-v2` via fastembed, **384 dims** | `bge-small-en-v1.5`; larger models |
| **Seed strategy** | **2D hybrid** — SHA256 manifest (multi-file + model ID) + `docker compose --profile seed run --rm seed` (ADR-005) | Auto-seed only on entrypoint; admin HTTP seed endpoint |
| **Manifest mismatch** | **Drop collection + full re-seed**; legacy volume without metadata = mismatch | Skip by `points_count` alone |
| **Fail-safe R1** | **`RAG_NOT_READY` (503)** in `start_interview` when Qdrant empty or manifest stale | Rely on `/health` only; fail only on `submit_answer` |
| **PR0 gate** | M1≥6/8 top-1 · M2≥80% top-3 overlap · M3=384 · M4 self-similarity ≥0.999 | Qualitative spike only |
| **CI gates** | PR1: golden test + smoke import · PR3: image size **log** · PR4: hard **650 MB** + no torch | Hard size gate from PR1 |
| **libgomp1** | PR1: README note · PR3: Dockerfile fix if needed | Fix in PR1 Dockerfile (avoid double Dockerfile churn) |
| **Config SSOT** | **Two layers:** core `embedding_config` (model + dims) · domain `rag_config` (collection + seed files) | Single `embedding_config` with domain paths in core |
| **VectorStore** | PR2 extends with metadata, drop, `points_count` before manifest logic *(✅ PR2)* | Direct `QdrantClient` in ingestion/readiness |
| **Readiness scope** | `check_rag_ready(collection_name, manifest_files, …)` derived from **requested domain** | Global constant `COLLECTION_ASYNC_MESSAGING` in service |

---

## Architectural adjustments (revisor-arquitetural — P0/P1)

Incorporated after review. Goal: keep `app/core/rag/` domain-agnostic; manifest and collection names live in each domain module.

### P0 — Config split (PR0/PR1)

| Module | Location | Contents |
|--------|----------|----------|
| `embedding_config.py` | `app/core/rag/` | `EMBEDDING_MODEL_ID`, `VECTOR_SIZE` only |
| `rag_config.py` | `app/domains/async_messaging/` | `COLLECTION_NAME`, `SEED_MANIFEST_FILES` |

**Consumers:**
- Core: `embeddings.py`, `vector_store.py` (import `VECTOR_SIZE`), golden/benchmark tooling
- Domain: `rag_ingestion.py`, golden tests, seed job
- `seed_manifest.py`: pure functions `compute_manifest_hash(files, model_id)` and `manifest_matches(...)` — **no** domain imports

### P0 — VectorStore extension (PR2 ✅)

Add to `app/core/rag/vector_store.py`:

| Method | Purpose |
|--------|---------|
| `get_collection_info(name) -> points_count, metadata` | Readiness + ingest decisions |
| `set_collection_metadata(name, dict)` | Persist manifest after seed |
| `drop_collection(name)` | Mismatch re-seed |

`rag_ingestion.py` and `rag_readiness.py` use **only** `VectorStore` — no direct `QdrantClient`.

### P0 — Readiness by domain (PR2 ✅)

```python
# rag_readiness.py — core domain-agnostic; uses get_vector_store() (settings QDRANT_*)
def check_rag_ready(
    collection_name: str,
    manifest_files: tuple[str, ...],
    *,
    vector_store: VectorStore | None = None,
    model_id: str = EMBEDDING_MODEL_ID,
) -> None:
    """Raises RagNotReady if collection empty or manifest stale."""
```

In `InterviewService.start_interview`:
1. Resolve domain module from registry
2. Read `COLLECTION_NAME` and `SEED_MANIFEST_FILES` from domain `rag_config` (not core constants)
3. Call `check_rag_ready(collection_name, manifest_files)` **after** topic validation, **before** `orchestrator.start()`

### P1 — Testability (PR0–PR2)

| Test file | Scope | Status |
|-----------|-------|--------|
| `tests/unit/core/rag/test_seed_manifest.py` | Hash stable; file/model change | ✅ PR0 |
| `tests/integration/rag/test_golden_retrieval.py` | 8/8 top-1 via Qdrant | ✅ PR1 Red |
| `tests/unit/core/rag/test_embeddings.py` | fastembed dims, batch, M4 | ✅ PR1 Red |
| `tests/unit/core/rag/test_vector_store_vector_size.py` | `VECTOR_SIZE` from config | ✅ PR1 Red |
| `tests/ci/test_no_torch_in_runtime_deps.py` | No torch/ST in runtime deps | ✅ PR1 Red |
| `tests/unit/core/rag/test_rag_readiness.py` | Mock `VectorStore`; qdrant_unavailable; settings host | ✅ PR2 (9 tests) |
| `tests/api/test_interviews_rag_not_ready.py` | 503 isolated empty/stale Qdrant | ✅ PR2 (3 tests) |
| `tests/api/test_interviews_submit_answer_rag_degraded.py` | No 503 on submit mid-session | ✅ PR2 (2 tests) |

**PR2 test total:** 14 tests · full suite **128 passed**.

**InterviewService injection (PR2):** optional `rag_readiness_check: Callable[[str, tuple[str, ...]], None]` (default: `_default_rag_readiness_check`).

**Golden queries:** all 8 `expected_top1_source` empirically validated in PR0 (GO). PR1 CI requires **8/8** after fastembed swap + re-seed.

---

## Delivery plan — 5 PRs (sequential)

Merge order: **PR0 → PR1 → PR2 → PR3 → PR4**. Each PR merges to `main` before the next starts.

**PR0 is a human gate:** without GO, do not open PR1. **GO recorded** — PR1 unlocked.

```
PR0 Spike GO/NO-GO  ✅ DONE
  → PR1 fastembed swap + golden CI  ✅ DONE
  → PR2 seed manifest + RAG_NOT_READY + compose seed profile  ✅ DONE
  → PR3 Docker slim + size log  ← current
  → PR4 CI hard gates + todo.md closure
```

### PR0 — GO/NO-GO fastembed parity ✅ DONE

**Goal:** Prove MiniLM parity before changing production embedder. No API/runtime behavior change.

| Create / change | Purpose | Status |
|-----------------|---------|--------|
| `app/core/rag/embedding_config.py` | `EMBEDDING_MODEL_ID`, `VECTOR_SIZE` only (core SSOT) | ✅ |
| `app/domains/async_messaging/rag_config.py` | `COLLECTION_NAME`, `SEED_MANIFEST_FILES` (domain SSOT) | ✅ |
| `app/domains/async_messaging/golden_queries.yaml` | 8 queries + validated `expected_top1_source` | ✅ |
| `app/core/rag/seed_manifest.py` | `compute_manifest_hash()` + `manifest_matches()` (PR2) | ✅ |
| `pyproject.toml` | `fastembed` in **dev** group only | ✅ |
| `docs/archive/rag_migration.md` | PR0 runbook (archived after GO) | ✅ |
| `docs/adr/ADR-005-qdrant-seed-strategy.md` | Seed 2D hybrid decision | ✅ |
| `tests/unit/core/rag/test_embedding_config.py` | Core SSOT boundary | ✅ |
| `tests/unit/domains/async_messaging/test_rag_config.py` | Domain SSOT | ✅ |
| `tests/unit/core/rag/test_seed_manifest.py` | Hash determinism | ✅ |
| `tests/unit/domains/async_messaging/test_golden_queries_schema.py` | Golden YAML schema | ✅ |

**GO criteria (all passed):**

| ID | Metric | Threshold | Result |
|----|--------|-----------|--------|
| M1 | Top-1 doc ID match (ST vs fastembed) | ≥ **6/8** | **7/8** |
| M2 | Top-3 overlap | ≥ **80%** | **100%** |
| M3 | Vector dimensions | **384** | **384** |
| M4 | Self-similarity | ≥ **0.999** | **1.0** |

**Notes:** Parity script removed after GO; runbook archived at `docs/archive/rag_migration.md`. Production embedder unchanged until PR1.

---

### PR1 — fastembed production swap ✅ DONE

**Goal:** Replace `EmbeddingProvider`; remove torch from lockfile; CI golden retrieval.

| Change | Purpose | Status |
|--------|---------|--------|
| `app/core/rag/embeddings.py` | fastembed `TextEmbedding`; import dims from `embedding_config` | ✅ |
| `app/core/rag/vector_store.py` | Remove `_VECTOR_SIZE`; import `VECTOR_SIZE` from `embedding_config` | ✅ |
| `pyproject.toml` / `uv.lock` | `fastembed` runtime; remove `sentence-transformers` | ✅ |
| `tests/integration/rag/test_golden_retrieval.py` | CI: **8/8** top-1 | ✅ |
| `tests/unit/core/rag/test_embeddings.py` | dims, batch, M4 | ✅ |
| `tests/unit/core/rag/test_vector_store_vector_size.py` | Config-driven vector size | ✅ |
| `tests/ci/test_no_torch_in_runtime_deps.py` | No torch/ST in prod deps | ✅ |
| `.github/workflows/ci.yml` | Golden test after seed step; smoke import | ✅ |
| `README.md` | `libgomp1` note for slim images | ✅ |

**Merge criteria:** full pytest green; no `torch` / `sentence-transformers` in runtime deps; golden 8/8 in CI.

**Post-merge (operators):** wipe stale Qdrant volume or re-seed — see runbook scenario A.

---

### PR2 — Seed manifest + RAG_NOT_READY ✅ DONE

**Goal:** Seed outside entrypoint; versioned manifest; fail-fast on start.

| Create / change | Purpose | Status |
|-----------------|---------|--------|
| `app/core/rag/vector_store.py` | **First:** `get_collection_info`, `set_collection_metadata`, `drop_collection` | ✅ |
| `app/core/rag/seed_manifest.py` | `manifest_matches()` for ingest + readiness | ✅ |
| `app/core/rag/rag_readiness.py` | `check_rag_ready(collection_name, manifest_files, …)` via `VectorStore` only | ✅ |
| `app/domains/async_messaging/rag_ingestion.py` | Manifest skip / drop+reseed / metadata | ✅ |
| `app/core/exceptions.py` + `app/api/errors.py` | `RagNotReady` → **503** `RAG_NOT_READY` on `start_interview` only | ✅ |
| `app/services/interview_service.py` | Resolve domain collection + manifest → readiness; injectable `rag_readiness_check` | ✅ |
| `scripts/docker-entrypoint.sh` | **Remove** unconditional seed — migrate + uvicorn only | ✅ |
| `scripts/run_seed.py` | Iterate registered domains | ✅ |
| `docker-compose.yml` | Service `seed` with `profiles: ["seed"]` → `run_seed.py` | ✅ |
| `docs/runbook/rag_seed.md` | Upgrade scenarios A–D | ✅ |
| `.github/workflows/ci.yml` | CI seed via `run_seed.py` | ✅ |
| `tests/unit/core/rag/test_rag_readiness.py` | Mock `VectorStore`; qdrant_unavailable; settings host | ✅ |
| `tests/api/test_interviews_rag_not_ready.py` | 503 with isolated empty/stale Qdrant | ✅ |
| `tests/api/test_interviews_submit_answer_rag_degraded.py` | Assert no 503 on submit when RAG unavailable | ✅ |

**Post-merge notes:** Operational logs in EN. `submit_answer` does **not** raise `RAG_NOT_READY` (mid-session degradation allowed). Full suite **128 passed** (14 PR2 tests).

**Optional (not implemented):** `EvaluatorAgent` logs ERROR if `chunks == []` (safety net only).

**First boot flow:**
```bash
docker compose up -d postgres vector-db
docker compose --profile seed run --rm seed
docker compose up -d api
```

---

### PR3 — Docker lean

**Goal:** Multi-stage build, `.dockerignore`, measure image size (non-blocking).

| Change | Purpose |
|--------|---------|
| `Dockerfile` | Multi-stage; `UV_NO_CACHE=1`; `libgomp1` if needed |
| `.dockerignore` | Exclude tests, git, caches, docs from build context |
| `.github/workflows/ci.yml` | Log `docker image inspect --format='{{.Size}}'` |
| `README.md` | Replace “~500 MB” with measured size |

---

### PR4 — CI hard gates + doc closure

**Goal:** Prevent regression.

| Change | Purpose |
|--------|---------|
| `scripts/ci/check_image_size.sh` | Fail if image **> 650 MB** |
| `scripts/ci/check_no_torch.sh` | Fail if `torch` / `sentence-transformers` in prod deps |
| `docs/todo.md` | Mark v0.2 items done |
| Optional | Pin `qdrant/qdrant` to specific tag |

---

## Technical specifications

### Config SSOT — two layers

**Core** — `app/core/rag/embedding_config.py`:

```python
EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_SIZE = 384
```

Consumers: `embeddings.py`, `vector_store.py`, `seed_manifest.py` (model ID only).

**Domain** — `app/domains/async_messaging/rag_config.py`:

```python
COLLECTION_NAME = "async_messaging"
SEED_MANIFEST_FILES = ("app/domains/async_messaging/rag_seed.yaml",)
```

Consumers: `rag_ingestion.py`, `rag_readiness` (via service), golden tests, seed job.

### Seed manifest algorithm

Pure function in `seed_manifest.py`:

```python
def compute_manifest_hash(files: tuple[str, ...], model_id: str) -> str: ...
```

```text
For each path in sorted(files):
  parts.append(f"{path}:{sha256(file_bytes)}")
parts.append(f"model:{model_id}")
SEED_MANIFEST_HASH = sha256("|".join(parts))
```

**Persist in Qdrant collection metadata (PR2):**
- `seed_manifest_hash`, `embedding_model_id`, `seed_manifest_files`, `seeded_at`

**Ingest logic (PR2)** — all via `VectorStore`:
1. `ensure_collection`
2. `get_collection_info` → if `points_count == 0` → seed
3. If metadata missing **or** hash ≠ computed → `drop_collection` → recreate → seed
4. If hash match → skip (log INFO)
5. After seed → `set_collection_metadata`

**Readiness (API):** does **not** auto-reseed — raises `RagNotReady`; operator runs seed job.

### `golden_queries.yaml` schema

Path: `app/domains/async_messaging/golden_queries.yaml`

```yaml
version: 1
domain: async_messaging
collection: async_messaging
queries:
  - id: gq_dlq_poison
    query: "<text>"
    topic: dead_letter_queue
    expected_top1_source: doc_dlq_03
```

8 queries (2 per topic): `dead_letter_queue`, `visibility_timeout`, `fan_out`, `batch_processing`.

PR1 CI requires **8/8** top-1 after fastembed swap + Qdrant re-seed.

### `RAG_NOT_READY` API contract (PR2)

| Field | Value |
|-------|-------|
| When | `start_interview` and Qdrant empty or manifest mismatch |
| HTTP | **503** |
| Code | `RAG_NOT_READY` |
| Not the same as | `INVALID_TOPIC`, `NO_QUESTIONS` |

Example body:
```json
{
  "detail": "Base de conhecimento RAG indisponível. Execute o seed antes de iniciar entrevistas.",
  "code": "RAG_NOT_READY"
}
```

---

## Runbook — four scenarios

### A — Upgrade PR1 (embedder change only)

1. `docker compose down`
2. Remove Qdrant volume (`qdrant_data`) or `docker compose down -v`
3. Re-seed (pre-PR2: entrypoint/ingest; post-PR2: profile `seed`)
4. Run golden tests

### B — Upgrade PR2+ (manifest in place)

1. `docker compose --profile seed run --rm seed`
2. Seed job detects hash mismatch → drop + reseed
3. `docker compose up -d api`

### C — Dev stale volume (old embedder, no metadata)

Symptoms: wrong retrieval, no error.  
Fix: wipe volume **or** run seed job.

### D — Qdrant unavailable mid-session (PR2+)

Symptoms: `submit_answer` continues; evaluator may run with `chunks == []`.  
Fix: restore Qdrant; **do not** re-seed unless manifest/embedder changed.

---

## Out of scope (v0.2)

- `/ready` endpoint (Postgres + Qdrant ping)
- Embedding sidecar / hosted API
- fastembed migration without re-index
- Admin HTTP seed endpoint
- Incremental per-document seed updates

---

## Agent pipeline

| Step | Agent | Deliverable | Status |
|------|-------|-------------|--------|
| 1 | `revisor-arquitetural-agent` | Module boundaries; P0/P1 ressalvas | **Done** |
| 2 | `escritor-testes-agent` | PR0 tests | **Done** |
| 3 | `executor-codigo-agent` | PR0 implementation | **Done** |
| 4 | **Miller** | GO/NO-GO validation | **Done** — GO (M1 7/8) |
| 5 | `escritor-testes-agent` | PR1 tests (TDD Red) | **Done** |
| 6 | `executor-codigo-agent` | PR1 implementation | **Done** |
| 7 | `refatorador-agent` / `revisor-codigo-agent` | PR1 review (optional) | Pending |
| 8 | `escritor-testes-agent` | PR2 tests (TDD Red) | **Done** |
| 9 | `executor-codigo-agent` | PR2 implementation | **Done** |
| 10 | `revisor-codigo-agent` | PR2 review | **Done** |
| 11 | `logs-agent` | PR2 operational log review | **Done** |
| 12 | `executor-codigo-agent` | PR2 log/fix follow-ups | **Done** |
| 13+ | PR3 cycle | Docker lean + size log | Pending |

After PR4: `documentacao-agent` (formal closure).

---

## Global v0.2 checklist

- [x] PR0: GO documented; config SSOT; golden queries; unit tests
- [x] PR1: fastembed in prod; torch removed; golden CI 8/8
- [x] PR2: seed decoupled; manifest; `RAG_NOT_READY`; runbook; 14 tests; 128 passed
- [ ] PR3: slim Docker; size logged
- [ ] PR4: hard CI gates; `todo.md` updated

---

## `todo.md` mapping (apply on PR4)

| Existing item | Action |
|---------------|--------|
| Torch CUDA critical (~L49) | Superseded → fastembed removes torch (PR1) |
| Seed every boot (~L60) | Done PR2 |
| Dockerfile / dockerignore (~L53–58) | Done PR3 |
| fastembed v2 (~L71) | Done PR1 (moved from v2 to v0.2) |
| README ~500 MB (~L68) | Done PR3 |
| `/ready` (~L64) | **Keep open** |
| Priority #10 fastembed evaluate | Replace with “fastembed PR0–PR4” |

---

## Current repo state

| Component | Today | After v0.2 |
|-----------|-------|------------|
| `embeddings.py` | fastembed (PR1 ✅) | fastembed |
| Config SSOT | Core + domain split (PR0 ✅) | ✅ |
| `vector_store.py` | `VECTOR_SIZE` + metadata/drop (PR1+PR2 ✅) | ✅ |
| `rag_readiness.py` | `check_rag_ready` → `RAG_NOT_READY` on start (PR2 ✅) | ✅ |
| `docker-entrypoint.sh` | Migrate + uvicorn only (PR2 ✅) | ✅ |
| Seed job | `run_seed.py` + compose profile `seed` (PR2 ✅) | ✅ |
| `Dockerfile` | Single-stage, no `.dockerignore` | Multi-stage slim (PR3) |
| Integration RAG test | Golden 8/8 top-1 (PR1 ✅) | ✅ |
| CI | Seed via `run_seed.py`; golden; no image gate | Golden + hard size + no-torch (PR4) |

---

## Conversation trace

Planning: `orquestrador` → `planejador` → `critico` → `tradeoffs` (Combo X) → `planejador` → `critico` → `revisor-arquitetural` (P0/P1 incorporated).

Implementation: PR0 complete (GO). PR1 complete (fastembed swap, golden 8/8, torch removed). PR2 complete (seed decoupled, manifest, `RAG_NOT_READY`, 14 tests, 128 passed).

Key trade-off: **Combo X** (monolithic fastembed) over torch-CPU-first, because **650 MB CI gate** requires fastembed.

**Next:** PR3 (Docker lean + size log) → PR4 (CI hard gates + `todo.md` closure).

---

*Update **Status** at the top and check off PR sections as merged.*
