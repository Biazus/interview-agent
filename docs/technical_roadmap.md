# Technical Roadmap — interview-agent

Strategic architecture and evolution plan for **interview-agent** (~v0.3).

For tactical debt and checkboxes, see `[todo.md](./todo.md)`.

---

## Current architectural vision

**v0.3** — FastAPI monolith + React SPA; layered backend with one live domain; production on Render + Supabase + Qdrant Cloud.

### Stack

- **Layering:** `api` → `services` → `repositories` → `agents`
- **Domains:** `DomainModule` + `register_domain()` (`app/core/domain/registry.py`); only `async_messaging` wired via `app/domains/async_messaging/bootstrap.py`
- **Persistence:** Postgres with partial unique indexes (`uq_interviews_candidate_active`, `uq_interview_turn_number` in `app/core/db/models.py`)
- **RAG:** Qdrant (`app/core/rag/`) + **fastembed** (ONNX) in-process embeddings (`app/core/rag/embeddings.py`)
- **LLM:** Groq primary → OpenRouter fallback (`app/core/llm/fallback.py`); evaluator and reporter both use Pydantic structured output
- **Frontend:** React SPA (Vercel); Bearer token in `localStorage`; CORS on API
- **Rate limiting:** slowapi, moving-window, `memory://` storage — limits apply per process (not shared across replicas)



### Critical path (`submit_answer`)

- Synchronous per request: evaluate (LLM + RAG) → optional final-turn report → persist
- Deliberate MVP trade-off — rationale and follow-ups in `[todo.md](./todo.md)`



### Runtime & deployment

- **Almost stateless HTTP:** singletons via `@lru_cache` (`get_llm_chain`, `get_embedding_provider`, `get_cached_domain`); embedding model and Qdrant clients remain in-process state
- **Container startup:** migrations + Uvicorn only (`scripts/docker-entrypoint.sh`); Qdrant seed is a separate compose profile job (`scripts/run_seed.py`)
- **Production:** Terraform provisions Render web service; Supabase Postgres + Qdrant Cloud referenced by env vars (see `infra/`)
- **RAG gate:** `start_interview` returns `503 RAG_NOT_READY` when the collection is empty or the manifest is stale
- **Image:** multi-stage build ~144 MB; CI hard gate at 650 MB (`scripts/ci/check_image_size.sh`)



### Strengths to preserve


| Area           | What works well                                                                                       |
| -------------- | ----------------------------------------------------------------------------------------------------- |
| Layering       | Domain exceptions decoupled from HTTP; clean service/repository split                                 |
| Multi-domain   | `DomainModule` + `register_domain()` + per-domain bootstrap                                           |
| LLM resilience | Groq → OpenRouter with transient/permanent error classification                                       |
| Persistence    | Partial unique indexes, `DuplicateTurn` handling, nested savepoint for report races                   |
| Auth           | Argon2, opaque tokens with SHA-256 hash, no PII in logs                                               |
| Public exposure | CORS, slowapi rate limits, answer/password length caps                                              |
| Tests          | Unit + API + integration in CI; LLM fakes, transactional fixtures, integration with state rehydration |


---



## Structural bottlenecks for scale


| Bottleneck                | Location                                                                         | Why it limits scale                                                                                           |
| ------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Embeddings in API process | `EmbeddingProvider`, `Dockerfile`                                                | fastembed in-process; thread-pool contention (`asyncio.to_thread` in `EvaluatorAgent`) under high concurrency |
| LLM on critical HTTP path | `InterviewService.submit_answer` → `OrchestratorAgent`                           | High P95 latency (RAG + evaluate + report); no backpressure; token cost on retry/duplicate                    |
| Health without readiness  | `app/api/main.py` `/health`                                                      | Orchestrator marks pod healthy when Postgres/Qdrant is down                                                   |
| In-memory rate limits     | `app/api/rate_limit.py` (`storage_uri="memory://"`)                              | Multi-replica deploy: each instance has its own bucket; effective limit scales with replica count             |
| No queue/workers          | Everything in Uvicorn                                                            | Cannot decouple LLM spikes from HTTP throughput; no DLQ for failed reports                                    |
| Partial idempotency       | DB constraints + LLM before commit                                               | `DuplicateTurn` protects turn integrity, but duplicate submit already spent tokens                            |
| Minimal observability     | `app/core/logging.py` plain text                                                 | No `request_id`, no token/latency/cost metrics per interview                                                  |
| No multi-tenant model     | Flat `candidates`, no `tenant_id`                                                | B2B would share the same namespace                                                                            |
| Domain coupled to deploy  | In-memory registry at startup                                                    | New domain requires redeploy; Qdrant collections per domain without central governance                        |


---



## Evolution horizons



### Short term (0–3 months) — harden the MVP


| #   | Initiative                              | Problem                                                   | Approach                                                                 | Effort     | Status |
| --- | --------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------ | ---------- | ------ |
| 1   | **Liveness vs readiness**               | `/health` returns OK without dependency checks            | `/health` (liveness) + `/ready` with Postgres + Qdrant ping              | Low        | Open   |
| 2   | **Structured output in evaluator**      | Text parsing vs JSON in reporter                          | Pydantic schema + `generate_structured()` (`EvaluationLLMOutput`)        | High       | **Done** |
| 3   | **Idempotency-Key on submit**           | Client retry after timeout wastes LLM tokens              | HTTP header → `idempotent_requests` table (key, response, TTL 24h)       | Medium     | Open   |
| 4   | **Payload limits + basic cost logging** | Tokens not structured in logs                             | Schema limits (4096 B answers); log `tokens_used` from `LLMResponse`      | Low        | Partial — limits done; cost logging open |
| 5   | **Test hardening**                      | Alembic drift, missing security API tests                 | Alembic in fixtures; ownership 404, report retry, duplicate turn tests   | Low–Medium | Open   |


**Target outcome:** Reliable single-replica deploy, stable LLM pipeline, safe public exposure.

---



### Medium term (3–12 months) — prepare horizontal scale


| #   | Initiative                    | Problem                                                                     | Approach                                                                                           | When                                   |
| --- | ----------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------- |
| 8   | **Async LLM workers**         | `submit_answer` blocks until evaluate (+ report) completes                  | Persist turn as `pending_evaluation` → queue (Redis Streams / SQS) → worker updates turn           | >50 concurrent submits or P95 > SLA    |
| 9   | **Embedding sidecar**         | `EmbeddingProvider` singleton per replica multiplies RAM                    | Microservice with fastembed/ONNX, or hosted API + Redis cache by text hash                         | 3+ API replicas or fastembed migration |
| 10  | **LLM circuit breaker**       | Sequential Groq → OpenRouter without shared state under peak                | Per-provider circuit breaker (Redis); deferred report retry                                        | Recurring rate limits                  |
| 11  | **RAG cache**                 | Every `evaluate()` embeds answer and queries Qdrant                         | LRU by `(topic, answer_hash)` or pre-computed context per `question_id`                            | RAG >30% of evaluate latency           |
| 12  | **Distributed observability** | Plain-text logs, no correlation                                             | JSON logs + `request_id`; OpenTelemetry; Prometheus (`llm_tokens_total`, `submit_latency_seconds`) | Team >1 or SLO defined                 |
| 13  | **Multi-domain governance**   | `DomainEnum` placeholders; registry + per-domain `get_orchestrator(domain)` | Plugin per `domains/<name>/` (bootstrap, Qdrant collection, versioned YAML); feature flags         | 2nd real domain (e.g. Kafka)           |
| 14  | **Auth lifecycle**            | Tokens accumulate without purge                                             | Periodic `DELETE WHERE expires_at < now()`; `POST /auth/logout`                                    | Before public registration             |
| 15  | **Separate** `InterviewState` | Metadata, history, report mixed (`interfaces.py` TODO)                      | `InterviewSession` + `InterviewHistory`                                                            | Before E2E complexity grows            |


**Target outcome:** Stateless API replicas, observable LLM cost, second domain live, optional async evaluate.

---



### Long term (12+ months) — platform & multi-tenant


| #   | Initiative                    | Problem                                                   | Approach                                                                             | When                                   |
| --- | ----------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------- |
| 16  | **Multi-tenant (B2B)**        | Flat B2C model                                            | `organizations`, `members`, `tenant_id`; Postgres RLS; Qdrant `tenant_domain` prefix | Product pivots to companies/recruiters |
| 17  | **A2A protocol**              | REST-only synchronous integration                         | Agent Card; async tasks via messaging; `OrchestratorAgent` as coordinator            | External agent ecosystem               |
| 18  | **Data partitioning**         | `interview_turns` + JSONB grows linearly                  | Partition by `created_at`; read replica for reports/analytics; cold archive (S3)     | >1M interviews                         |
| 19  | **Intelligent model routing** | Same model for evaluate and report; no budget             | Smaller model for evaluate, larger for report; daily quota per tenant                | LLM cost >10% of ops budget            |
| 20  | **Frontend streaming**        | No SSE/WebSocket; feedback hidden from candidate          | SSE for progress during long submits; optional `FallbackLLMProvider.stream`          | Interactive UX beyond current REST SPA     |


**Target outcome:** B2B-ready platform with tenant isolation, async agent integration, and cost controls.

---



## Architecture decision records (candidates)


| ADR     | Topic                 | Proposed decision                                      | Alternatives                                |
| ------- | --------------------- | ------------------------------------------------------ | ------------------------------------------- |
| ADR-001 | Where embeddings run  | In-process until 2 replicas; then fastembed sidecar    | Hosted embedding API; GPU node pool         |
| ADR-002 | Sync vs async LLM     | Sync while P95 within SLA; queue when P95 exceeds SLA or >50 concurrent submits | Aggressive timeout only                     |
| ADR-003 | Unified LLM contract  | Pydantic structured output for evaluate **and** report — **implemented**        | Tool calling; few-shot text parsing         |
| ADR-004 | Submit idempotency    | `Idempotency-Key` HTTP + Postgres table                | DB constraints only (`DuplicateTurn`)       |
| ADR-005 | Qdrant seed strategy  | Init job + manifest hash                               | Conditional seed in entrypoint              |
| ADR-006 | Observability stack   | OpenTelemetry + JSON structured logs                   | Extra log fields only (interim)             |
| ADR-007 | Multi-tenant model    | `tenant_id` + Postgres RLS when B2B                    | Schema per tenant; single-tenant per deploy |
| ADR-008 | Candidate feedback    | Keep hidden (current) or expose level only             | Full real-time feedback                     |
| ADR-009 | Message queue         | Redis Streams → SQS in production                      | Celery; Kafka (overkill for MVP)            |
| ADR-010 | Interview state model | Split `InterviewSession` / `InterviewHistory`          | Keep monolithic `InterviewState`            |


---

