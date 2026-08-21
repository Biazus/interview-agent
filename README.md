# Interview Agent

An AI-powered technical interview platform. Candidates authenticate via a REST API, run adaptive interviews grounded in domain knowledge (RAG), and receive structured reports. Behind the scenes, agents orchestrate question selection, retrieval-augmented context, and rubric-based evaluation.

## Overview

**API layer** — FastAPI endpoints for auth, discovery, and the interview lifecycle (start → answer → report).

**Agent layer** — Each domain (e.g. **async messaging** with SQS, SNS, Lambda) bundles:

- **Question bank** — curated questions by topic and difficulty
- **RAG retriever** — semantic search over domain knowledge (Qdrant + embeddings)
- **Rubric provider** — criteria for scoring answers (weak / medium / strong examples)

A central **registry** wires domains at startup. The orchestrator picks a domain, asks questions, retrieves context, and uses an LLM (Groq with OpenRouter fallback) to evaluate answers.

## Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.13, [uv](https://docs.astral.sh/uv/) |
| API | FastAPI, Uvicorn |
| Database | PostgreSQL 16, SQLAlchemy async + asyncpg, Alembic |
| Auth | Argon2 passwords, opaque Bearer tokens (SHA-256 in DB) |
| Vectors | Qdrant, fastembed (ONNX) |
| LLM | Groq → OpenRouter fallback chain |
| CI | GitHub Actions (Postgres + Qdrant service containers) |

> **Embeddings runtime:** Production uses **fastembed** (ONNX) instead of PyTorch/sentence-transformers. The multi-stage Dockerfile installs `libgomp1` for ONNX Runtime on Debian slim.

> **Docker image size:** Multi-stage build (Aug 2026, `linux/amd64`): **151,330,784 bytes (~144 MB)** — down from ~8.54 GB with torch. CI logs size on each run (non-blocking).

## Quick start (Docker)

The API runs in Docker by default. On container start the entrypoint waits for Qdrant, applies migrations, then starts Uvicorn. **Qdrant seed is a separate one-off job** — run it before the first interview (see below).

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set GROQ_API_KEY and OPENROUTER_API_KEY
```

### 2. First boot (Postgres, Qdrant, seed, API)

```bash
docker compose up -d postgres vector-db
docker compose --profile seed run --rm seed
docker compose up -d api
```

The seed job loads domain knowledge into Qdrant (embeddings may take a minute on first run). Data persists in the `qdrant_data` volume — you only need to re-run seed after embedder or manifest changes (see [docs/current_plan.md](docs/current_plan.md) PR2 runbook).

**Later restarts** (volumes intact): `docker compose up -d` is enough.

OpenAPI docs: http://localhost:8000/docs

Logs: `docker compose logs -f api`

### What runs automatically

| Step | Where |
|------|--------|
| Postgres + Qdrant | `docker compose` services |
| `alembic upgrade head` | API container entrypoint |
| Qdrant seed (RAG) | One-off `seed` service (`docker compose --profile seed run --rm seed`) |
| Uvicorn on `:8000` | API container entrypoint |

You do **not** need to run migrations or start Uvicorn manually when using Docker. You **do** need to run the seed job once before starting interviews (or after RAG data changes). `POST /interviews` returns **503** `RAG_NOT_READY` if Qdrant is empty or stale.

## Local tooling (uv)

Install [uv](https://docs.astral.sh/uv/) on the host for tests, lint, and Alembic outside Docker:

```bash
uv sync --group dev
```

Use this when running pytest or ruff on the host. The test database `interview_agent_test` is created by [scripts/init-databases.sql](scripts/init-databases.sql); schema is applied by pytest fixtures in [tests/conftest.py](tests/conftest.py).

**Integration tests** need Qdrant with seed data. Start Postgres and Qdrant, run the seed job, then run tests against `localhost:6333`:

```bash
docker compose up -d postgres vector-db
docker compose --profile seed run --rm seed   # or: uv run python scripts/run_seed.py
uv run pytest tests/integration
```

Or run the full suite:

```bash
docker compose up -d postgres vector-db   # if not already running
docker compose --profile seed run --rm seed
uv run pytest
```

## API endpoints

All error responses use `{"detail": "...", "code": "ERROR_CODE"}`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | — | Liveness check |
| `GET` | `/domains` | — | List available interview domains |
| `GET` | `/topics?domain=` | — | List topics for a domain (`domain` required) |
| `POST` | `/auth/register` | — | Register candidate (does **not** auto-login) |
| `POST` | `/auth/login` | — | Returns Bearer `access_token` (TTL 24h by default) |
| `POST` | `/interviews` | Bearer | Start interview (`domain`, `topic`, `difficulty`) |
| `GET` | `/interviews/active` | Bearer | Get candidate's active interview |
| `POST` | `/interviews/{id}/answers` | Bearer | Submit answer (no level/feedback in response) |
| `GET` | `/interviews/{id}/report` | Bearer | Get report (retry if LLM failed on last submit) |

Protected routes expect `Authorization: Bearer <token>`.

### Interview flow

1. **Register** → `POST /auth/register`
2. **Login** → `POST /auth/login` → store `access_token`
3. **Discover** → `GET /domains`, `GET /topics?domain=async_messaging`
4. **Start** → `POST /interviews` — one active interview per candidate
5. **Answer** → `POST /interviews/{id}/answers` — repeat until finished; report is generated on the final submit
6. **Report** → `GET /interviews/{id}/report` — if LLM failed during final submit, call again to retry generation

**Ownership:** accessing another candidate's interview returns `404` with code `INTERVIEW_NOT_FOUND` (no information leak).

### Common error codes

| Code | HTTP | When |
|------|------|------|
| `MISSING_TOKEN` / `INVALID_TOKEN` | 401 | Auth header missing or invalid |
| `INVALID_CREDENTIALS` | 401 | Wrong email/password |
| `EMAIL_ALREADY_REGISTERED` | 409 | Duplicate registration |
| `ACTIVE_INTERVIEW_EXISTS` | 409 | Candidate already has an active interview |
| `INTERVIEW_NOT_FOUND` / `NO_ACTIVE_INTERVIEW` | 404 | Interview not found or no active interview |
| `INTERVIEW_ALREADY_FINISHED` | 409 | Submit on finished interview |
| `INTERVIEW_NOT_FINISHED` | 409 | Report requested before interview ends |
| `INVALID_DOMAIN` / `INVALID_TOPIC` | 400 | Unknown domain or topic |
| `EMPTY_ANSWER` | 422 | Blank answer |
| `RAG_NOT_READY` | 503 | Qdrant empty or seed manifest stale on `POST /interviews` |
| `LLM_UNAVAILABLE` | 503 | All LLM providers failed |

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `postgresql+asyncpg://interview:interview@localhost:5432/interview_agent` | Async Postgres connection string |
| `GROQ_API_KEY` | Yes | — | Groq API key (primary LLM) |
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key (fallback LLM) |
| `AUTH_TOKEN_TTL_SECONDS` | No | `86400` | Bearer token lifetime (24h) |
| `LOG_LEVEL` | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `QDRANT_HOST` | No | `localhost` | Qdrant hostname (`vector-db` inside Docker Compose) |
| `QDRANT_PORT` | No | `6333` | Qdrant HTTP port |

Copy [.env.example](.env.example) as a starting point. When using `docker compose`, `QDRANT_HOST` is set to `vector-db` for the API service automatically.

## Running tests

Prerequisites: [uv](https://docs.astral.sh/uv/) on the host and Docker for Postgres/Qdrant.

```bash
uv sync --group dev
docker compose up -d postgres vector-db
docker compose --profile seed run --rm seed   # or: uv run python scripts/run_seed.py
```

```bash
# Unit tests (fast)
uv run pytest tests/unit

# API tests (Postgres — interview_agent_test)
uv run pytest tests/api

# Integration tests (Qdrant on localhost:6333 — seed via run_seed.py)
uv run pytest tests/integration

# Full suite
uv run pytest
```

CI runs the same suites with Postgres and Qdrant service containers (see [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Docker services

| Service | Port | Notes |
|---------|------|-------|
| `api` | 8000 | Waits for Qdrant, migrations, then Uvicorn |
| `seed` | — | One-off RAG ingest (`profiles: ["seed"]`) — runs `scripts/run_seed.py` |
| `postgres` | 5432 | Postgres 16, user/db `interview` |
| `vector-db` | 6333 | Qdrant |
| `localstack` | 4566 | Optional (`--profile messaging`) — SQS/SNS/Lambda for future use |

## Logging

Structured logging via `app/core/logging.py`. `configure_logging()` runs at app startup using `LOG_LEVEL` from settings. Services log with `extra={}` fields (interview/candidate UUIDs, error types). No PII in logs — emails, tokens, and answer text are never logged.

## Project layout

```
app/
├── api/                  # FastAPI app, routers, schemas, dependencies, error handlers
├── agents/               # Orchestrator, evaluator, reporting
├── services/             # auth_service, interview_service, discovery_service
├── repositories/         # SQLAlchemy persistence (candidates, interviews, tokens)
├── core/
│   ├── auth/             # Password hashing, token generation/validation
│   ├── db/               # Engine, session, ORM models
│   ├── domain/           # Registry, interfaces (Question, Rubric, Chunk)
│   ├── llm/              # Providers, fallback chain, structured output
│   ├── rag/              # Embeddings, vector store, retriever
│   ├── exceptions.py     # Domain exceptions (mapped to HTTP in api/errors.py)
│   ├── logging.py        # Logging configuration and helpers
│   └── settings.py       # Pydantic settings from .env
└── domains/
    └── async_messaging/  # First domain: questions, rubrics, RAG seed data
```

New domains (Kafka, RabbitMQ, etc.) can be added by implementing the three interfaces and registering a factory in the registry.

## Further reading

- [docs/current_plan.md](docs/current_plan.md) — PR2 seed job, manifest, and `RAG_NOT_READY` runbook
- [docs/todo.md](docs/todo.md) — dependency audit and follow-up backlog
