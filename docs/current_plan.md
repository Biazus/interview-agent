# Current Plan — v0.2 Deploy Hardening (fastembed + seed híbrido)

**Status:** Planning complete · **Architectural review:** approved with reservations (P0/P1 incorporated) · **Implementation:** not started  
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
| Seed | `ingest_seed_documents()` on **every** API boot | Decoupled init job + manifest hash |
| RAG failure mode | Empty retrieval → LLM evaluates without context (silent) | **`RAG_NOT_READY` (503)** on `start_interview` |

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
| **VectorStore** | PR2 extends with metadata, drop, `points_count` before manifest logic | Direct `QdrantClient` in ingestion/readiness |
| **Readiness scope** | `check_rag_ready(collection_name)` derived from **requested domain** | Global constant `COLLECTION_ASYNC_MESSAGING` in service |

---

## Architectural adjustments (revisor-arquitetural — P0/P1)

Incorporated after review. Goal: keep `app/core/rag/` domain-agnostic; manifest and collection names live in each domain module.

### P0 — Config split (PR0/PR1)

| Module | Location | Contents |
|--------|----------|----------|
| `embedding_config.py` | `app/core/rag/` | `EMBEDDING_MODEL_ID`, `VECTOR_SIZE` only |
| `rag_config.py` | `app/domains/async_messaging/` | `COLLECTION_NAME`, `SEED_MANIFEST_FILES` |

**Consumers:**
- Core: `embeddings.py`, `vector_store.py` (import `VECTOR_SIZE`), benchmark script
- Domain: `rag_ingestion.py`, golden tests, seed job
- `seed_manifest.py`: pure functions `compute_manifest_hash(files, model_id)` and `manifest_matches(...)` — **no** domain imports

### P0 — VectorStore extension (PR2, before manifest logic)

Add to `app/core/rag/vector_store.py`:

| Method | Purpose |
|--------|---------|
| `get_collection_info(name) -> points_count, metadata` | Readiness + ingest decisions |
| `set_collection_metadata(name, dict)` | Persist manifest after seed |
| `drop_collection(name)` | Mismatch re-seed |

`rag_ingestion.py` and `rag_readiness.py` use **only** `VectorStore` — no direct `QdrantClient`.

### P0 — Readiness by domain (PR2)

```python
# rag_readiness.py
def check_rag_ready(collection_name: str, *, vector_store: VectorStore | None = None) -> None:
    """Raises RagNotReady if collection empty or manifest stale."""
```

In `InterviewService.start_interview`:
1. Resolve domain module from registry
2. Read `COLLECTION_NAME` from domain `rag_config` (not a core constant)
3. Call `check_rag_ready(collection_name)` **after** topic validation, **before** `orchestrator.start()`

### P1 — Testability (PR0–PR2)

| Test file | Scope |
|-----------|-------|
| `tests/unit/core/rag/test_seed_manifest.py` | Hash stable; file change; model ID change; legacy missing metadata |
| `tests/unit/core/rag/test_rag_readiness.py` | Mock `VectorStore`: empty, hash match, mismatch, no metadata |
| `tests/api/test_interviews_rag_not_ready.py` | 503 with **isolated** empty/stale Qdrant (not CI pre-seeded state) |
| `tests/api/test_interviews_submit_answer_rag_degraded.py` | `submit_answer` **does not** 503 when Qdrant empty mid-session (intentional) |

**InterviewService injection (PR2):** optional `rag_readiness_check: Callable[[str], None]` (default: real implementation) — enables unit test of 503 without Qdrant; API test complements with real empty collection.

**PR0 blocker:** all 8 `expected_top1_source` values in `golden_queries.yaml` must be **empirically validated** via benchmark before merge — no guessed doc IDs.

---

## Delivery plan — 5 PRs (sequential)

Merge order: **PR0 → PR1 → PR2 → PR3 → PR4**. Each PR merges to `main` before the next starts.

**PR0 is a human gate:** without GO, do not open PR1.

```
PR0 Spike GO/NO-GO
  → PR1 fastembed swap + golden CI
  → PR2 seed manifest + RAG_NOT_READY + compose seed profile
  → PR3 Docker slim + size log
  → PR4 CI hard gates + todo.md closure
```

### PR0 — GO/NO-GO fastembed parity

**Goal:** Prove MiniLM parity before changing production embedder. No API/runtime behavior change.

| Create / change | Purpose |
|-----------------|---------|
| `app/core/rag/embedding_config.py` | `EMBEDDING_MODEL_ID`, `VECTOR_SIZE` only (core SSOT) |
| `app/domains/async_messaging/rag_config.py` | `COLLECTION_NAME`, `SEED_MANIFEST_FILES` (domain SSOT) |
| `app/domains/async_messaging/golden_queries.yaml` | 8 fixed queries + empirically validated `expected_top1_source` |
| `scripts/benchmark_embedding_parity.py` | Runs M1–M4; exit 0=GO, 1=NO-GO |
| `pyproject.toml` | `fastembed` in **dev** group only (PR0) |
| `docs/rag_migration.md` | How to run benchmark |
| `docs/adr/ADR-005-qdrant-seed-strategy.md` | Seed 2D hybrid decision |
| `tests/unit/core/rag/test_seed_manifest.py` | Hash determinism (stub API; full impl PR2) |

**GO criteria:**

| ID | Metric | Threshold |
|----|--------|-----------|
| M1 | Top-1 doc ID match (ST vs fastembed) | ≥ **6/8** queries |
| M2 | Top-3 overlap (expected source in top-3) | ≥ **80%** |
| M3 | Vector dimensions | **384** |
| M4 | Self-similarity `cosine(embed(t), embed(t))` | ≥ **0.999** |

**Miller validation:**
```bash
uv sync --group dev
uv run python scripts/benchmark_embedding_parity.py --verbose
```

---

### PR1 — fastembed production swap

**Goal:** Replace `EmbeddingProvider`; remove torch from lockfile; CI golden retrieval.

| Change | Purpose |
|--------|---------|
| `app/core/rag/embeddings.py` | fastembed `TextEmbedding`; import dims from `embedding_config` |
| `app/core/rag/vector_store.py` | Remove local `_VECTOR_SIZE`; import `VECTOR_SIZE` from `embedding_config` |
| `pyproject.toml` / `uv.lock` | `fastembed` runtime; remove `sentence-transformers` |
| `tests/integration/rag/test_golden_retrieval.py` | CI: **8/8** top-1 (stricter than PR0 GO) |
| `tests/unit/core/rag/test_embeddings.py` | dims, batch, M4 |
| `.github/workflows/ci.yml` | Golden test after seed step; smoke import |
| `README.md` | `libgomp1` note for slim images |

**Merge criteria:** full pytest green; no `torch` / `sentence-transformers` in runtime deps; golden 8/8 in CI.

**Post-merge (operators):** wipe stale Qdrant volume or re-seed — see runbook below.

---

### PR2 — Seed manifest + RAG_NOT_READY

**Goal:** Seed outside entrypoint; versioned manifest; fail-fast on start.

| Create / change | Purpose |
|-----------------|---------|
| `app/core/rag/vector_store.py` | **First:** `get_collection_info`, `set_collection_metadata`, `drop_collection` |
| `app/core/rag/seed_manifest.py` | Pure `compute_manifest_hash(files, model_id)` + compare helpers |
| `app/core/rag/rag_readiness.py` | `check_rag_ready(collection_name: str)` via `VectorStore` only |
| `app/domains/async_messaging/rag_ingestion.py` | Drop+reseed; write metadata; uses domain `rag_config` + `VectorStore` |
| `app/core/exceptions.py` + `app/api/errors.py` | `RagNotReady` → **503** `RAG_NOT_READY` |
| `app/services/interview_service.py` | Resolve domain collection → readiness check; injectable `rag_readiness_check` |
| `scripts/docker-entrypoint.sh` | **Remove** unconditional seed |
| `scripts/run_seed.py` | Iterate registered domains (avoids hardcoded domain import in Compose) |
| `docker-compose.yml` | Service `seed` with `profiles: ["seed"]` → `run_seed.py` |
| `docs/runbook/rag_seed.md` | Upgrade scenarios A–D |
| `tests/unit/core/rag/test_seed_manifest.py` | Full unit coverage |
| `tests/unit/core/rag/test_rag_readiness.py` | Mock `VectorStore` scenarios |
| `tests/api/test_interviews_rag_not_ready.py` | 503 with isolated empty/stale Qdrant |
| `tests/api/test_interviews_submit_answer_rag_degraded.py` | Assert no 503 on submit when RAG unavailable |

**Optional:** `EvaluatorAgent` logs ERROR if `chunks == []` (does not raise — safety net only).

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

Consumers: `embeddings.py`, `vector_store.py`, benchmark script, `seed_manifest.py` (model ID only).

**Domain** — `app/domains/async_messaging/rag_config.py`:

```python
COLLECTION_NAME = "async_messaging"
SEED_MANIFEST_FILES = ("app/domains/async_messaging/rag_seed.yaml",)
```

Consumers: `rag_ingestion.py`, `rag_readiness` (via service resolving domain), golden tests, seed job.

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

Call site passes `SEED_MANIFEST_FILES` + `EMBEDDING_MODEL_ID` from respective config modules.

**Persist in Qdrant collection metadata:**
- `seed_manifest_hash`
- `embedding_model_id`
- `seed_manifest_files`
- `seeded_at` (ISO timestamp)

**Ingest logic (PR2)** — all via `VectorStore`:
1. `ensure_collection`
2. `get_collection_info` → if `points_count == 0` → seed
3. If metadata missing **or** hash ≠ computed → `drop_collection` → recreate → seed
4. If hash match → skip (log INFO)
5. After seed → `set_collection_metadata` with hash, model ID, files, `seeded_at`

**Readiness (API):** does **not** auto-reseed — `check_rag_ready(domain_collection)` raises `RagNotReady`; operator runs seed job. Collection name comes from domain `rag_config`, not core.

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
    expected_top1_source: doc_dlq_03   # must exist in rag_seed.yaml
```

**Planned 8 queries (2 per topic):** `dead_letter_queue`, `visibility_timeout`, `fan_out`, `batch_processing`.

Seed doc IDs in repo today: `doc_dlq_01`…`doc_dlq_06`, `doc_visibility_01/02`, `doc_fanout_01/02`, `doc_batch_01/02`.

> **PR0 blocker:** run benchmark and **materialize** all 8 `expected_top1_source` in YAML before merge. Do not guess top-1 IDs. PR1 CI requires **8/8** — unstable queries that pass GO (6/8) but fail one ID block PR1.

### `RAG_NOT_READY` API contract

| Field | Value |
|-------|-------|
| When | `start_interview` and Qdrant collection empty or manifest mismatch |
| HTTP | **503** |
| Code | `RAG_NOT_READY` |
| Not the same as | `INVALID_TOPIC` (question bank), `NO_QUESTIONS` (orchestrator exhaustion) |

Example body:
```json
{
  "detail": "Base de conhecimento RAG indisponível. Execute o seed antes de iniciar entrevistas.",
  "code": "RAG_NOT_READY"
}
```

---

## Runbook — three scenarios

### A — Upgrade PR1 (embedder change only)

1. `docker compose down`
2. Remove Qdrant volume (`qdrant_data`) or full `docker compose down -v`
3. `docker compose up -d` + seed (explicit step pre-PR2; post-PR2 use profile `seed`)
4. Run golden tests / manual RAG script

### B — Upgrade PR2+ (manifest in place)

1. Run `docker compose --profile seed run --rm seed`
2. Seed job detects hash mismatch → drop + reseed automatically
3. `docker compose up -d api` (entrypoint: migrate + uvicorn only)

### C — Dev stale volume (vectors from old embedder, no metadata)

Symptoms: retrieval quality wrong, no error.  
Fix: wipe volume **or** run seed job (treats missing metadata as mismatch).

### D — Qdrant unavailable mid-session (PR2+)

Symptoms: interview already started; `submit_answer` continues; evaluator may run with `chunks == []` (degraded quality, no 503).  
Fix: restore Qdrant service; **do not** re-seed unless manifest/embedder changed. Optional `EvaluatorAgent` ERROR log is safety net only — not a user-facing failure.

---

## Out of scope (v0.2)

- `/ready` endpoint (Postgres + Qdrant ping) — future PR
- Embedding sidecar / hosted API
- fastembed migration without re-index (re-index is mandatory once)
- Admin HTTP seed endpoint
- Incremental per-document seed updates

---

## Agent pipeline (after this document)

| Step | Agent | Deliverable | Status |
|------|-------|-------------|--------|
| 1 | `revisor-arquitetural-agent` | Validate module boundaries; P0/P1 ressalvas | **Done** — approved with reservations; plan updated |
| 2 | `escritor-testes-agent` | PR0 tests (benchmark exit codes, golden schema, `test_seed_manifest` stub) | Pending |
| 3 | `executor-codigo-agent` | PR0 implementation | Pending |
| 4 | **Miller** | Run benchmark; GO/NO-GO | Pending |
| 5+ | TDD cycle per PR | escritor-testes → executor → refatorador → revisor-codigo → condutor-testes | Pending |

After PR2: consider `seguranca-agent`. After PR4: `documentacao-agent`.

---

## Global v0.2 checklist

- [ ] PR0: benchmark GO documented
- [ ] PR1: fastembed in prod; torch removed; golden CI 8/8
- [ ] PR2: seed decoupled; manifest; `RAG_NOT_READY`; runbook
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

See final plan section in agent transcripts for proposed `todo.md` diff text.

---

## Current repo state (pre-implementation)

| Component | Today | After v0.2 |
|-----------|-------|------------|
| `embeddings.py` | `SentenceTransformer` | fastembed |
| Config SSOT | Duplicated constants (`_VECTOR_SIZE`, `_COLLECTION_NAME`) | Core `embedding_config` + domain `rag_config` |
| `vector_store.py` | `ensure_collection`, `upsert`, `search` | + metadata, drop, `get_collection_info` |
| `Dockerfile` | Single-stage, no `.dockerignore` | Multi-stage slim |
| `docker-entrypoint.sh` | Always seeds Qdrant | Migrate + uvicorn only |
| Seed job | Hardcoded domain import | `scripts/run_seed.py` via domain registry |
| Integration RAG test | `len(chunks) > 0` | Golden top-1 doc ID |
| CI | Seed step; no image gate | Golden + hard size + no-torch |

---

## Conversation trace (for context restart)

Planning flow used: `orquestrador-agent` → `planejador-agent` → `critico-agent` → `tradeoffs-agent` (Combo X) → `planejador-agent` (PR split + patches) → `critico-agent` (revalidation) → `planejador-agent` (final plan + `RAG_NOT_READY` + golden queries) → `revisor-arquitetural-agent` (P0/P1 incorporated into this doc).

Key trade-off resolved: **Combo X** (monolithic fastembed path) over phased torch-CPU-first, because **650 MB CI gate** requires fastembed.

---

*When implementation starts, update **Status** at the top and check off PR sections as merged.*
