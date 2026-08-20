# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
