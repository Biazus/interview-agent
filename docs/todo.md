# TODO — Technical debt & improvement backlog

Consolidated technical debt and improvement backlog (Aug 2026).  
Severity: **Critical** · **High** · **Medium** · **Low** · **Info**

---

## LLM & agents

- [x] **[Critical]** `EvaluatorAgent` migrated to structured output via `generate_structured_with_response()` and `EvaluationLLMOutput` in `app/agents/evaluator.py` (replaces free-text `NIVEL:`/`FEEDBACK:` parsing).

- [ ] **[Medium]** RAG retrieval runs synchronously in a thread (`asyncio.to_thread` in evaluator) — acceptable for v1, but a bottleneck under high concurrency.  
  **Recommendation:** Revisit when scaling; consider async embedding client or dedicated worker.

- [ ] **[Info]** Evaluation feedback is not exposed in the API (by design) — document as an explicit product decision if it stays that way.

---

## Security

- [ ] **[High]** Login creates a new token without revoking previous ones (`auth_service.py`); no cleanup of expired tokens.  
  **Impact:** `auth_tokens` table grows indefinitely.  
  **Recommendation:** Background purge job + optional `POST /auth/logout` with token revocation.

- [x] **[Low]** Rate limiting on `/auth/*` — slowapi shared limit (`RATE_LIMIT_AUTH`, default 5/min) on register and login; global limit via custom middleware (`app/api/rate_limit.py`).

- [ ] **[Medium]** Rate limit storage is `memory://` (per process). Multi-replica deploy applies independent buckets on each instance — no shared limit across pods.  
  **Recommendation:** Redis (or equivalent) backend when scaling beyond one API replica.

- [x] **[Info]** CORS configured in `app/api/main.py` via `CORS_ORIGINS` in settings.

---

## Deploy & performance

- [ ] **[High]** `/health` returns only `{"status":"ok"}` (`app/api/main.py`) — no dependency checks.  
  **Impact:** Orchestrators mark pod healthy when Postgres or Qdrant is down.  
  **Recommendation:** Add readiness endpoint with Postgres + Qdrant ping.

- [ ] **[Low]** HuggingFace model `all-MiniLM-L6-v2` (~90 MB) downloaded at runtime on first use, not baked into the image.  
  **Recommendation:** Optional — pre-download in Dockerfile (`HF_HOME`) for predictable cold start.

---

## Tests

- [ ] **[High]** README documents `404 INTERVIEW_NOT_FOUND` for cross-candidate access, but no API test covers it.  
  **Impact:** Silent IDOR regression if query logic changes.  
  **Recommendation:** Add API test with two authenticated candidates.

- [ ] **[Medium]** Missing API tests for documented flows: report retry after LLM failure on final turn, `DuplicateTurn` on concurrent submit.  
  **Recommendation:** Add tests in `tests/api/` using `FailingReportLLM` and concurrent submit scenarios.

- [ ] **[Medium]** No direct unit tests for `InterviewService` or `AuthService` — complex logic only covered indirectly.  
  **Recommendation:** Add `tests/unit/services/test_interview_service.py` and `test_auth_service.py`.

- [ ] **[Medium]** Expired token behaviour tested only with fake repo (`test_token_validator.py`), not via API.  
  **Recommendation:** Add case in `tests/api/test_auth.py`.

- [ ] **[Medium]** `StructuredOutputError` → `503` mapping for report generation not tested end-to-end.  
  **Recommendation:** API test with failing structured LLM.

- [ ] **[Info]** No automated coverage reporting (`pytest-cov`) in CI — blind spots unknown.  
  **Recommendation:** Add coverage step with a minimum threshold.

- [ ] **[Info]** Evaluator + RAG integration only partially covered (rehydration test); no integration test with seeded Qdrant + real retrieval path.

---

## Code quality & architecture

- [ ] **[Medium]** `InterviewService` returns `dict` instead of `InterviewResponse` or TypedDict — weak internal typing.  
  **Recommendation:** Return typed models to reduce refactor risk.

- [ ] **[Medium]** `InterviewState` mixes metadata, history, and report (TODO in `app/core/domain/interfaces.py`).  
  **Recommendation:** Split into `InterviewSession` and `InterviewHistory` for cleaner persistence/rehydration.

- [ ] **[Medium]** `StaticAsyncMessagingRubricProvider` does not nominally implement `RubricProvider` protocol.  
  **Recommendation:** Declare protocol explicitly for contract consistency.

- [ ] **[Medium]** No global handler for unmapped exceptions (`app/api/errors.py`).  
  **Impact:** Unhandled errors return non-standard 500 without `{"detail","code"}` shape.  
  **Recommendation:** Generic handler that logs and returns consistent JSON.

- [x] **[Medium]** Dead code: `get_active_domain()` in `app/api/dependencies.py` is never used.  
  **Recommendation:** Remove or wire into orchestrator factory.

- [x] **[Low]** `app/bootstrap.py` — dual bootstrap paths (import side-effect + `bootstrap_domains()` in API lifespan).  
  **Recommendation:** Idempotent double invocation accepted; no refactor this cycle.

---

## Observability

- [ ] **[Low]** `logging.basicConfig` with plain text (`app/core/logging.py`); no correlation/request ID.  
  **Recommendation:** JSON logging + `request_id` middleware for distributed debugging.

- [ ] **[Low]** No metrics or tracing for LLM token usage, latency, or cost (noted in `notes.txt`).  
  **Recommendation:** OpenTelemetry or structured log fields for tokens/latency/cost per call.

---

## Dependencies (`pyproject.toml`)

- [ ] **[High]** `pytest` is listed under runtime `dependencies` instead of dev.  
  **Recommendation:** Move `pytest` to `dependency-groups.dev` alongside `pytest-asyncio`. Production Docker uses `uv sync --frozen --no-dev` and should not install test tooling.

- [ ] **[Medium]** `python-dotenv` is declared as a direct runtime dependency but is not imported in application code.  
  **Recommendation:** Remove from `dependencies`; `pydantic-settings` already brings it in transitively for `env_file=".env"`.

- [ ] **[Low]** `[project.scripts] interview-agent = "interview_agent:main"` is configured while `package = false`, so the entry point is non-functional.  
  **Recommendation:** Remove the script entry until a real CLI exists, or fix packaging and implement `interview_agent:main`.

- [ ] **[Low]** Pinning strategy is inconsistent: `ruff==0.6.1` is exact while most other packages use `>=`.  
  **Recommendation:** Document the intentional pin for reproducible CI, or align on a single strategy.

- [ ] **[Low]** `uvicorn` is installed without the `[standard]` extra (no reload / websockets helpers out of the box).  
  **Recommendation:** Optional — add `uvicorn[standard]` for local dev if reload or WebSockets are needed.

---

## CI/CD

- [ ] **[Info]** No automated CVE / vulnerability scan in CI.  
  **Recommendation:** Add a CI step (`uv export` + `pip-audit`) or enable Dependabot / GitHub Advisory monitoring; prioritize `fastapi`, `sqlalchemy`, `torch`, `pyyaml`, and `argon2-cffi`.

- [ ] **[Medium]** No static type checking (`mypy` / `pyright`) in CI.  
  **Recommendation:** Add typecheck on critical modules (`services`, `agents`, `core`).

- [ ] **[Info]** Pre-commit runs full pytest (`always_run: true` in `.pre-commit-config.yaml`) — slow commits.  
  **Recommendation:** Keep ruff in hook; run pytest only in CI.

---

## Repo hygiene

- [ ] **[Low]** `notes.txt` contains personal/internal notes and roadmap items that should not live in the repo.  
  **Recommendation:** Remove from repo or move to private issues/wiki.

---

## Accepted as-is (no action required)

- `groq` + `openai` (two LLM SDKs) — justified by Groq → OpenRouter fallback chain.
- `openai` used only as OpenRouter HTTP adapter — mature SDK; replacing with raw `httpx` adds maintenance for little gain.
- `httpx` in dev only — correct; runtime receives it transitively via `qdrant-client` and `openai`.
- API / persistence stack (`fastapi`, `sqlalchemy`, `asyncpg`, `alembic`, `argon2-cffi`, `email-validator`, `pydantic-settings`) — appropriate for v1.
- `submit_answer` calls LLM before persisting — correct to avoid invalid turns; rare DB failure after LLM implies token cost (accepted trade-off).
- `tests/conftest.py` uses `Base.metadata.create_all` instead of `alembic upgrade head` — acceptable while models and migrations stay in sync (single migration today); drift risk revisited when schema changes become non-trivial (partial indexes, data migrations). Optional future: smoke `alembic upgrade head` step in CI.

---

## Priority quick reference

| # | Item | Severity | Effort | Status |
|---|------|----------|--------|--------|
| 1 | Structured output in `EvaluatorAgent` | Critical | High | **Done** |
| 2 | Readiness check (Postgres + Qdrant) | High | Low | Open |
| 3 | API tests: ownership 404, report retry, duplicate turn | High | Low | Open |
| 4 | Move `pytest` to dev; remove dead deps | High | Low | Open |
| 5 | Token purge + optional logout | High | Medium | Open |
| 6 | Distributed rate limit (Redis) for multi-replica | Medium | Medium | Open |
| 7 | JSON logging + request ID + LLM token metrics | Low | Medium | Open |
