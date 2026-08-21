# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **CI hard gates (PR4)**
  - `scripts/ci/check_image_size.sh` — fail if Docker image exceeds **650 MB**
  - `scripts/ci/check_no_torch.sh` — fail if `torch` or `sentence-transformers` in runtime deps
  - Qdrant pinned to `v1.12.5` in compose and CI

- **Multi-stage Docker (PR3)**
  - Multi-stage `Dockerfile` with `UV_NO_CACHE=1` and `libgomp1`
  - `.dockerignore` excludes tests, git, caches, and docs from build context
  - Measured image size ~144 MB (CI logs size after build)

- **Seed manifest + RAG readiness**
  - `VectorStore`: `get_collection_info`, `set_collection_metadata`, `drop_collection`
  - `seed_manifest.manifest_matches()` for ingest and readiness checks
  - `check_rag_ready(collection_name, manifest_files, …)` — domain-agnostic; uses `get_vector_store()` (`QDRANT_*` settings)
  - `RagNotReady` → **503** `RAG_NOT_READY` on `start_interview` (not on `submit_answer`)
  - Injectable `rag_readiness_check: Callable[[str, tuple[str, ...]], None]` on `InterviewService`
  - Decoupled seed: `scripts/run_seed.py`, compose profile `seed`, entrypoint migrate + uvicorn only
  - Runbook [`docs/runbook/rag_seed.md`](docs/runbook/rag_seed.md) (scenarios A–D)
  - CI seed via `run_seed.py`
  - 14 PR2 tests (readiness, API 503, submit degraded); full suite 128 passed

### Changed

- **fastembed production swap**
  - Replaced `sentence-transformers` / torch with **fastembed** (ONNX) in `EmbeddingProvider`
  - Removed torch from runtime dependencies; golden retrieval 8/8 in CI
  - `VECTOR_SIZE` from `embedding_config` SSOT

- **Docker startup (PR2)** — API entrypoint no longer seeds Qdrant on every boot; operator runs seed job explicitly before first start or after manifest/embedder change.

## [0.1.0] - 2026-08-20

### Added

- **REST API (Phases 0–4)** — nine endpoints for health, discovery, auth, and interview lifecycle:
  - `GET /health`, `GET /domains`, `GET /topics`
  - `POST /auth/register`, `POST /auth/login`
  - `POST /interviews`, `GET /interviews/active`, `POST /interviews/{id}/answers`, `GET /interviews/{id}/report`
- **Authentication** — Argon2 password hashing, opaque Bearer tokens (SHA-256 stored in DB), configurable TTL (`AUTH_TOKEN_TTL_SECONDS`, default 24h). Register does not auto-login.
- **Interview flow** — one active interview per candidate; report generated on final answer submit; `GET /report` retries LLM generation if the last submit failed. Cross-candidate access returns `404 INTERVIEW_NOT_FOUND`.
- **Persistence** — PostgreSQL 16 with SQLAlchemy async, Alembic migrations, repository layer.
- **Agent pipeline** — orchestrator, evaluator, and reporting agents with domain registry and RAG (Qdrant + sentence-transformers).
- **LLM providers** — Groq primary with OpenRouter fallback.
- **Docker** — `docker-compose` for API, Postgres, and Qdrant; Dockerfile runs migrations on container start.
- **CI** — GitHub Actions with Postgres and Qdrant service containers; unit, API, and integration test suites.
- **Domain exceptions (Phase 5)** — typed `AppError` hierarchy in `app/core/exceptions.py`, mapped to HTTP status codes in `app/api/errors.py`.
- **Structured logging (Phase 5)** — `configure_logging()` with `LOG_LEVEL` setting; structured `extra={}` in auth, interview, fallback, and orchestrator paths. No PII in logs.
- **Docker startup** — API entrypoint waits for Qdrant, runs migrations, seeds RAG documents, then starts Uvicorn. `QDRANT_HOST` / `QDRANT_PORT` settings for container networking.

### Fixed

- **ReportLLMOutput** — normalize empty `pontos_fortes`, `pontos_fracos`, and `sugestoes` lists from LLM output with readable fallback strings before validation.

[0.1.0]: https://github.com/Biazus/interview-agent/releases/tag/v0.1.0
