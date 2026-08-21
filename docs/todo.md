# TODO — Technical debt & improvement backlog

Consolidated follow-ups from **dependencias-agent** (dependency audit), **analista-generico-agent** (architecture/code review), and **Docker image size analysis** (Aug 2026).  
Severity: **Critical** · **High** · **Medium** · **Low** · **Info**

---

## LLM & agents

- [ ] **[Critical]** `EvaluatorAgent._parse_response()` relies on free-text parsing (`NIVEL:` / `FEEDBACK:`) in `app/agents/evaluator.py`, while `ReportingAgent` already uses structured output via `generate_structured()`.  
  **Impact:** Intermittent parse failures surface as `503 LLM_UNAVAILABLE`.  
  **Recommendation:** Migrate evaluation to `generate_structured()` with a Pydantic schema (mirror `app/agents/reporting_schema.py`).

- [ ] **[Medium]** RAG retrieval runs synchronously in a thread (`asyncio.to_thread` in evaluator) — acceptable for v1, but a bottleneck under high concurrency.  
  **Recommendation:** Revisit when scaling; consider async embedding client or dedicated worker.

- [ ] **[Info]** Evaluation feedback is not exposed in the API (by design) — document as an explicit product decision if it stays that way.

---

## Security

- [ ] **[Critical]** `SubmitAnswerRequest.answer` has `min_length=1` but no `max_length` (`app/api/schemas/interviews.py`).  
  **Impact:** Oversized payloads → DoS, LLM cost, unbounded `answer_text` growth.  
  **Recommendation:** Add `max_length` (e.g. 4–8 KB) in schema and enforce in service layer.

- [ ] **[Low]** Password schema has `min_length=8` but no `max_length`.  
  **Impact:** Argon2 on very large passwords can cause CPU DoS.  
  **Recommendation:** Add `max_length` (e.g. 128) in auth schemas.

- [ ] **[High]** Login creates a new token without revoking previous ones (`auth_service.py`); no cleanup of expired tokens.  
  **Impact:** `auth_tokens` table grows indefinitely.  
  **Recommendation:** Background purge job + optional `POST /auth/logout` with token revocation.

- [ ] **[Low]** No rate limiting on `/auth/*`.  
  **Impact:** Brute-force on login/register.  
  **Recommendation:** Middleware or reverse-proxy limits before exposing publicly.

- [ ] **[Info]** No CORS configured — required when a browser frontend is added.

---

## Deploy & performance

### Docker image size (observed: **8.54 GB** — `interview-agent-api:latest`)

Root cause: `sentence-transformers` → `torch 2.13` resolves the **full CUDA 13 + NVIDIA stack** on Linux PyPI (~2.5+ GB of wheels) even though the container has **no GPU**. The `uv sync` layer alone is ~5.4 GB. The old “~500 MB” estimate counted only the torch wheel, not NVIDIA/Triton or build cache overhead.

> **v0.2 progress:** PR0–PR4 complete (fastembed, seed decoupled, multi-stage Docker ~144 MB, CI hard gates). **`/ready` endpoint remains open.**

- [x] **[Critical]** PyTorch 2.13 Linux wheel pulls **CUDA toolkit + nvidia-*** (`cublas`, `cudnn`, `nccl`, `triton`, etc.) via default PyPI resolution — useless in a CPU-only container.  
  **Impact:** ~2.5+ GB wasted; slow pull/build; large CVE surface; no performance gain without GPU.  
  **Recommendation:** Force **torch CPU-only** via `tool.uv.sources` / PyTorch CPU index (`download.pytorch.org/whl/cpu`); regenerate `uv.lock`; rebuild and measure. **Target: ~1–1.5 GB image.**  
  **Progress:** **Superseded PR1** — fastembed removed torch from runtime deps; PR3 multi-stage build ~144 MB; PR4 CI hard gate 650 MB.

- [x] **[High]** Dockerfile installs deps in a single stage with no cache cleanup (`RUN pip install uv && uv sync --frozen --no-dev`).  
  **Impact:** Possible duplication of uv wheel cache + `.venv` in the final layer.  
  **Recommendation:** Set `UV_NO_CACHE=1` (or `rm -rf /root/.cache/uv` after sync); consider **multi-stage build** copying only `.venv` into the runtime image.  
  **Progress:** **Done PR3** — multi-stage Dockerfile, `UV_NO_CACHE=1`, `.dockerignore`.

- [x] **[High]** No `.dockerignore` — local artifacts (`__pycache__`, `.pytest_cache`, `.git`, `tests/`, etc.) may inflate `COPY . .`.  
  **Recommendation:** Add `.dockerignore` with standard Python/Docker exclusions.  
  **Progress:** **Done PR3**.

- [x] **[High]** `docker-entrypoint.sh` runs `ingest_seed_documents()` on **every** API start (loads `SentenceTransformer`, re-embeds seed docs).  
  **Impact:** Slow cold start (~1 min first boot); model may load twice (seed subprocess + API process); unnecessary CPU on restarts.  
  **Recommendation:** Seed only when Qdrant collection is empty/missing; or use a pre-populated Qdrant volume snapshot.  
  **Progress:** **Done PR2** — entrypoint is migrate + uvicorn only; seed via `scripts/run_seed.py` + compose profile `seed`; manifest skip on match ([`docs/runbook/rag_seed.md`](./runbook/rag_seed.md), ADR-005).

- [ ] **[High]** `/health` returns only `{"status":"ok"}` (`app/api/main.py`) — no dependency checks.  
  **Impact:** Orchestrators mark pod healthy when Postgres or Qdrant is down.  
  **Recommendation:** Add readiness endpoint with Postgres + Qdrant ping.

- [ ] **[Medium]** README still references “~500 MB” torch impact — understates observed **8.54 GB** image.  
  **Recommendation:** Update after CPU-only build with measured size.  
  **Progress:** **Done PR3** — README updated with measured multi-stage image size (~144 MB).

- [x] **[Medium — v2]** Replace `sentence-transformers` with **fastembed** (ONNX Runtime) or a dedicated embedding sidecar.  
  **Impact:** Removes torch entirely from API image; **requires re-indexing Qdrant** (vectors from different embedders are not comparable).  
  **Recommendation:** Benchmark `all-MiniLM-L6-v2` parity; plan migration. **Target API image: ~200–400 MB.**  
  **Progress:** **Done PR1** — fastembed in production; golden 8/8; torch/ST removed from runtime deps. Sidecar remains a scale option (ADR-001).

- [ ] **[Low]** HuggingFace model `all-MiniLM-L6-v2` (~90 MB) downloaded at runtime on first use, not baked into the image.  
  **Recommendation:** Optional — pre-download in Dockerfile (`HF_HOME`) for predictable cold start.

---

## Tests

- [ ] **[High]** `tests/conftest.py` uses `Base.metadata.create_all`, not Alembic migrations.  
  **Impact:** Schema drift between migrations and tests; production-only bugs.  
  **Recommendation:** Run `alembic upgrade head` in test fixtures.

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

- [ ] **[Medium]** `StaticAsyncMessagingQuestionBank` always returns `candidates[0]` (TODO line 21) — deterministic, low variety.  
  **Recommendation:** Randomization or rotation strategy.

- [ ] **[Medium]** `StaticAsyncMessagingRubricProvider` does not nominally implement `RubricProvider` protocol.  
  **Recommendation:** Declare protocol explicitly for contract consistency.

- [ ] **[Medium]** No global handler for unmapped exceptions (`app/api/errors.py`).  
  **Impact:** Unhandled errors return non-standard 500 without `{"detail","code"}` shape.  
  **Recommendation:** Generic handler that logs and returns consistent JSON.

- [ ] **[Medium]** Dead code: `get_active_domain()` in `app/api/dependencies.py` is never used.  
  **Recommendation:** Remove or wire into orchestrator factory.

- [ ] **[Low]** `app/bootstrap.py` duplicates domain registration and is not referenced.  
  **Recommendation:** Remove or document for script-only use.

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

- [x] **[Medium]** `qdrant/qdrant:latest` in compose and CI — non-reproducible builds.  
  **Recommendation:** Pin to a specific Qdrant version tag.  
  **Progress:** **Done PR4** — pinned to `qdrant/qdrant:v1.12.5` in compose and CI.

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

---

## Priority quick reference (top 12)

| # | Item | Severity | Effort |
|---|------|----------|--------|
| 1 | **Torch CPU-only** — remove CUDA/NVIDIA from Docker image | Critical | Low | **Superseded PR1** (fastembed); **Done PR3/PR4** (~144 MB + 650 MB gate) |
| 2 | Dockerfile cache cleanup + `.dockerignore` + multi-stage | High | Low | **Done PR3** |
| 3 | Structured output in `EvaluatorAgent` | Critical | High | Open |
| 4 | `max_length` on answer/password | Critical | Low | Open |
| 5 | Idempotent / conditional Qdrant seed on entrypoint | High | Low | **Done PR2** |
| 6 | Readiness check (Postgres + Qdrant) | High | Low | Open (`/ready` — out of v0.2 scope) |
| 7 | API tests: ownership 404, report retry, duplicate turn | High | Low | Open |
| 8 | Move `pytest` to dev; remove dead deps | High | Low | Open |
| 9 | Alembic-based test fixtures | High | Medium | Open |
| 10 | Evaluate **fastembed** (v2 — re-index Qdrant) | Medium | High | **Done PR1** (v0.2 PR0–PR4) |
| 11 | Token purge + optional logout | High | Medium |
| 12 | JSON logging + request ID + LLM token metrics | Low | Medium |
