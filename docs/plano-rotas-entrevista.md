# Plano técnico — Rotas FastAPI de Entrevistas (v1)

**Projeto:** interview-agent  
**Status:** Aprovado (planejador + crítico + revisor arquitetural)  
**Requisitos:** [requisitos-rotas-entrevista.md](./requisitos-rotas-entrevista.md)  
**Última atualização:** 2026-08-19

---

## 1. Visão geral

Expor o fluxo do `OrchestratorAgent` via API REST com auth por usuário, Postgres (SQLAlchemy async) e 9 endpoints. O núcleo de agentes **não é reescrito** — a API persiste e reidrata `InterviewState` entre requests.

### Vereditos do pipeline

| Etapa | Resultado |
|-------|-----------|
| Planejador | Plano em 7 fases |
| Crítico | Aprovado com ressalvas (incorporadas) |
| Revisor arquitetural | Aprovado com ressalvas (incorporadas neste doc) |

### Arquitetura de camadas

```
HTTP async (routers + schemas + errors)
    ↓ Depends()
Services (casos de uso; LLM fora da transação DB)
    ↓
Repositories (AsyncSession; CRUD + reidratação InterviewState)
    ↓
OrchestratorAgent (já existe)
```

### Novos pacotes

| Pacote | Responsabilidade |
|--------|------------------|
| `app/core/settings.py` | Config unificada (DB, auth TTL, LLM keys) |
| `app/core/db/` | Engine async, session factory, modelos ORM |
| `app/core/auth/` | Argon2, tokens opacos, `TokenValidator` |
| `app/repositories/` | Repos async + `interview_mapper.py` |
| `app/services/` | `AuthService`, `InterviewService`, `DiscoveryService` |
| `app/api/routers/` | Rotas por domínio HTTP |
| `app/api/schemas/` | Pydantic request/response |
| `app/api/errors.py` | `APIError`, handlers, catálogo `code` |

### Boundaries

| Responsabilidade | Onde | Evitar |
|------------------|------|--------|
| FastAPI `Depends` | `app/api/dependencies.py` | Engine/session no router |
| Session lifecycle | `app/core/db/session.py` | `AsyncSession` nos agents |
| Factory de agentes | `dependencies.py` ou `services/factories.py` | `OrchestratorAgent` no router |
| Mapeamento ORM ↔ domain | `app/repositories/` | ORM no orchestrator |
| Erros HTTP | `app/api/errors.py` | `HTTPException` espalhado em services |

---

## 2. Stack técnica

| Item | Decisão |
|------|---------|
| Python | **3.13** (Dockerfile, CI, `pyproject.toml`) |
| ORM | SQLAlchemy 2.x **async** + `asyncpg` |
| Migrations | Alembic (engine sync no `env.py` para migrations) |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| Senha | Argon2 (`argon2-cffi`) |
| Token | Opaco (`secrets.token_urlsafe(32)`); hash SHA-256 em `auth_tokens` |
| TTL token | 24h; sem refresh na v1 |
| Registro | Auto-registro; email + senha (≥ 8 chars); **não** auto-loga |

### Dependências (`pyproject.toml`)

```toml
"sqlalchemy[asyncio]>=2.0",
"asyncpg>=0.30",
"alembic>=1.14",
"argon2-cffi>=23.1",
"email-validator>=2.0",
"httpx>=0.28",  # dev — TestClient
```

---

## 3. Rotas (9 endpoints)

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/health` | Pública | App up (sem check Postgres) |
| `GET` | `/domains` | Pública | Domínios do registry |
| `GET` | `/topics?domain=` | Pública | Tópicos do domínio (breaking change vs `/topics` atual) |
| `POST` | `/auth/register` | Pública | Registro candidato |
| `POST` | `/auth/login` | Pública | Login → bearer token |
| `POST` | `/interviews` | Bearer | Inicia entrevista |
| `GET` | `/interviews/active` | Bearer | Retoma entrevista ativa |
| `POST` | `/interviews/{id}/answers` | Bearer | Submete resposta |
| `GET` | `/interviews/{id}/report` | Bearer | Relatório final |

**Fora de v1:** `/questions`, `GET /interviews/{id}`, abandon, rate limit, JWT, lock otimista, CORS (confirmar same-origin).

---

## 4. Reidratação (`InterviewState` ↔ Postgres)

### O problema

`InterviewState` é um dataclass em memória. Entre requests HTTP o estado vive no Postgres em tabelas normalizadas — não como blob.

### Tabelas

| Tabela | Representa |
|--------|--------------|
| `interviews` | Metadados + snapshot da pergunta atual |
| `interview_turns` | Histórico append-only (pergunta + resposta + avaliação) |
| `interview_reports` | Relatório (quando gerado) |

### Reidratar (`to_state`)

1. `interview_turns` ordenados → `history: list[tuple[Question, Evaluation]]`
2. `finished` ← `interview.status == 'finished'`
3. Se `active`: `current_question` do snapshot em `interviews`
4. Se `finished`: placeholder interno (não exposto na API)
5. Se `interview_reports` existe: preencher `state.report`

### Persistir (após `submit_answer`)

| Dado | Destino |
|------|---------|
| Novo turno | `INSERT interview_turns` (`turn_number = len(history)`) |
| Snapshot pergunta | `UPDATE interviews` (`current_question_*`) |
| Contador | `questions_answered = len(history)` — mesma transação |
| Encerramento | `status='finished'`, `finished_at` se `finished=true` |
| Relatório | `INSERT interview_reports` se gerado com sucesso |

### Gate Fase 3 (bloqueia Fase 4)

Testes sem HTTP:

1. `start()` → persist → reload → estado equivalente
2. Após K turnos: `history`, `current_question`, `finished` corretos
3. `Evaluation.raw_response` JSONB round-trip sem perda
4. `finished` + report → reidratação com `state.report` preenchido
5. `submit_answer` no state reidratado ≡ fluxo só-memória (LLM mock)

---

## 5. Schema DB

### Tabelas

```
candidates
├── id (UUID PK)
├── email (UNIQUE, lowercase)
├── password_hash
├── created_at

auth_tokens
├── id (UUID PK)
├── token_hash (UNIQUE, SHA-256 hex)
├── candidate_id (FK)
├── expires_at
├── created_at
└── INDEX token_hash

interviews
├── id (UUID PK)
├── candidate_id (FK)
├── domain (varchar)
├── status ('active' | 'finished')
├── topic, difficulty
├── current_question_* (snapshot, nullable se finished)
├── questions_answered
├── created_at, updated_at, finished_at
└── UNIQUE (candidate_id) WHERE status = 'active'

interview_turns
├── id (UUID PK)
├── interview_id (FK)
├── turn_number — UNIQUE (interview_id, turn_number)
├── question_* (snapshot)
├── answer_text
├── evaluation_level, evaluation_feedback
├── evaluation_provider, evaluation_model
├── evaluation_raw_response (JSONB)
└── created_at

interview_reports
├── interview_id (PK, FK)
├── overall_summary, strengths, weaknesses, suggestions (JSONB)
├── total_questions
└── generated_at
```

### Migrations (B-02)

| Onde | Como |
|------|------|
| **Docker** | `scripts/docker-entrypoint.sh`: `alembic upgrade head` → uvicorn (runtime, não build) |
| **CI** | Step `alembic upgrade head` após Postgres healthy |
| **Local** | `docker compose up` aplica via entrypoint |

> **Nota produção:** múltiplas réplicas rodando migrate em paralelo — fora de escopo v1.

---

## 6. Fluxos críticos

### 6.1 `POST /interviews/{id}/answers`

```
1. Validações: ownership (404), finished (409), answer vazio (422)
2. Carregar interview + turns → reidratar InterviewState
3. orchestrator = get_orchestrator(DomainEnum(interview.domain))

4. try: new_state = await orchestrator.submit_answer(state, answer)
   except LLMProviderError | EvaluationParseError: → 503 (SEM writes)

5. report_to_persist = None
   if new_state.finished:
       try: report_to_persist = await orchestrator.get_report(new_state)
       except LLMProviderError: report_to_persist = None  # retry em GET

6. BEGIN transação:
     INSERT turn + UPDATE interview (+ INSERT report se ok)
   COMMIT
   IntegrityError turn_number → 409 DUPLICATE_TURN
   IntegrityError active interview → 409 ACTIVE_INTERVIEW_EXISTS

7. Response sem level/feedback; finished=true sem current_question
```

**Regra crítica (revisor arquitetural):** LLM **fora** da transação DB. Falha no passo 4 = estado inalterado (D-04).

**Último turno + report fail:** persistir turno + `finished` mesmo sem report; `GET /report` retenta.

### 6.2 `GET /interviews/{id}/report`

```
1. ownership → 404
2. não finished → 409 INTERVIEW_NOT_FINISHED
3. report no DB → retorna (idempotente, sem LLM)
4. reidratar → await orchestrator.get_report(state)
5. falha LLM → 503 sem persistir
6. sucesso → persistir + retornar
```

### 6.3 Evaluator (A-06)

- `EvaluationParseError` quando parse falha
- **Remover** fallback silencioso para `"medium"`
- Mapear para 503 `LLM_UNAVAILABLE`

---

## 7. DI e cache

### Settings unificado (A-07)

`app/core/settings.py` substitui/estende `app/core/llm/config.py`:

```python
class Settings(BaseSettings):
    DATABASE_URL: str
    AUTH_TOKEN_TTL_SECONDS: int = 86400
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str
```

### Cache de domínio (A-01 + revisor)

**Não** alterar `get_domain()` globalmente. Usar wrapper:

```python
@lru_cache
def get_cached_domain(domain: DomainEnum) -> DomainModule:
    return get_domain(domain)  # factory sem cache interno

@lru_cache
def get_llm_chain() -> FallbackLLMProvider: ...

def get_orchestrator(domain: DomainEnum) -> OrchestratorAgent:
    module = get_cached_domain(domain)
    return OrchestratorAgent(
        domain=module,
        llm=get_llm_chain(),
        selector=NaiveSelector(module),
    )
```

Testes: `get_cached_domain.cache_clear()` no conftest.

### Lifespan (M-05)

```python
register_async_messaging_domain()
for domain in DomainEnum:
    try: get_cached_domain(domain)
    except DomainNotRegisteredError: pass
```

### Auth (M-03)

```python
class TokenValidator(Protocol):
    async def validate(self, raw_token: str) -> UUID | None: ...
```

Validação com `secrets.compare_digest`; token nunca logado.

---

## 8. Catálogo de error codes

Resposta padrão: `{ "detail": "...", "code": "MACHINE_CODE" }` (PT + code).

| HTTP | `code` |
|------|--------|
| 400 | `INVALID_DOMAIN`, `INVALID_TOPIC`, `VALIDATION_ERROR` |
| 401 | `MISSING_TOKEN`, `INVALID_TOKEN`, `INVALID_CREDENTIALS` |
| 404 | `INTERVIEW_NOT_FOUND`, `NO_ACTIVE_INTERVIEW` |
| 409 | `EMAIL_ALREADY_REGISTERED`, `ACTIVE_INTERVIEW_EXISTS`, `INTERVIEW_ALREADY_FINISHED`, `INTERVIEW_NOT_FINISHED`, `DUPLICATE_TURN` |
| 422 | `EMPTY_ANSWER` |
| 503 | `LLM_UNAVAILABLE` |

Handlers globais na **Fase 1** (`app/api/errors.py`).

---

## 9. Fases de implementação

### Fase 0 — Infra (bloqueante)

| Ação | Arquivos |
|------|----------|
| Python 3.13 | `Dockerfile`, CI, `.python-version` |
| Deps async | `pyproject.toml` |
| Postgres | `docker-compose.yml` |
| Settings | `app/core/settings.py` |
| DB async | `app/core/db/` |
| Alembic | `alembic.ini`, `alembic/env.py`, `001_initial_schema.py` |
| Entrypoint | `scripts/docker-entrypoint.sh` |
| `get_db` async | `app/api/dependencies.py` |

**Done:**
- [ ] `docker compose up` sobe api + postgres + qdrant; migrations automáticas
- [ ] `alembic upgrade head` do zero
- [ ] Smoke async `SELECT 1`

---

### Fase 1 — Auth + errors (A-08)

| Ação | Arquivos |
|------|----------|
| `errors.py` + handlers | `app/api/errors.py`, `main.py` |
| Argon2, tokens | `app/core/auth/` |
| `TokenValidator` | `interfaces.py`, `db_token_validator.py` |
| Repos + service | `repositories/`, `services/auth_service.py` |
| Rotas | `routers/auth.py`, `schemas/auth.py` |
| Dependency | `get_current_candidate_id` |

**Done:**
- [ ] Register 201 sem token; login 200
- [ ] Erros auth com `detail` + `code`
- [ ] Testes unitários password, token, validator
- [ ] HTTP: register → login → rota protegida

---

### Fase 2 — Discovery

| Ação | Arquivos |
|------|----------|
| `DiscoveryService` | `services/discovery_service.py` |
| Router | `routers/discovery.py` |
| Remover `/topics` legado | `main.py` |

**Done:**
- [ ] `GET /domains`, `GET /topics?domain=`
- [ ] Domínio inválido → 400
- [ ] Breaking change documentado

---

### Fase 3 — Persistência + reidratação (GATE)

| Ação | Arquivos |
|------|----------|
| Mapper | `repositories/interview_mapper.py` |
| Repository | `repositories/interview_repository.py` |
| `EvaluationParseError` | `app/agents/evaluator.py` |
| `get_orchestrator` | `dependencies.py` |

**Done (GATE — bloqueia Fase 4):**
- [ ] Round-trip mapper active/finished
- [ ] Reidratação N turns ≡ memória
- [ ] Round-trip orchestrator após reload
- [ ] Partial unique → IntegrityError
- [ ] `questions_answered == len(turns)`
- [ ] `get_cached_domain` cacheado

---

### Fase 4 — Rotas de entrevista

| Ação | Arquivos |
|------|----------|
| `InterviewService` | `services/interview_service.py` |
| Schemas + router | `schemas/interviews.py`, `routers/interviews.py` |
| IntegrityError → 409 | service/repository |

**Done:**
- [ ] Happy path completo
- [ ] Report no último submit (se LLM ok)
- [ ] Report fail no submit → finished persistido; GET retry
- [ ] LLM fail evaluate → 503 sem persist
- [ ] Resposta sem level/feedback
- [ ] `GET /interviews/active` retoma sessão
- [ ] Segunda entrevista ativa → 409

---

### Fase 5 — Logging e polish

| Ação | Arquivos |
|------|----------|
| Logging estruturado | services |
| Remover `print()` | `orchestrator.py` |
| Catálogo completo | `errors.py` |

**Done:**
- [ ] Sem token em logs
- [ ] `evaluation_raw_response` persistido
- [ ] Sem `print()` em produção

---

### Fase 6 — Testes HTTP + CI

| Ação | Arquivos |
|------|----------|
| Fixtures | `tests/api/conftest.py` |
| Fake LLM | `tests/fakes/llm.py` |
| Testes | `tests/api/test_*.py` |
| CI Postgres | `.github/workflows/ci.yml` |

**Cenários obrigatórios:** 401, 404, 409, 422, 503, happy path E2E, report retry.

**Done:**
- [ ] `pytest tests/api` verde local
- [ ] CI com Postgres + migrations
- [ ] Critérios globais do doc de requisitos §10

---

## 10. Dependências entre fases

```
Fase 0 ──► Fase 1 ──► Fase 4
              │
Fase 0 ──► Fase 2 ──┘
              │
Fase 0 ──► Fase 3 (GATE) ──► Fase 4 ──► Fase 5 ──► Fase 6
```

Fases 1, 2 e 3 paralelizáveis após Fase 0. **Fase 4 exige 1 + 2 + 3.**

---

## 11. Pipeline TDD (próximo passo)

Ordem sugerida para `escritor-testes-agent`:

1. Fase 0/1: settings, errors, auth
2. Fase 2: discovery
3. **Gate Fase 3:** round-trip mapper (bloqueia implementação de rotas)
4. Pré-Fase 4: `EvaluationParseError`, orchestrator async
5. Fase 4–6: services, rotas, HTTP E2E

---

## 12. Arquivos existentes a modificar

| Arquivo | Mudança |
|---------|---------|
| `Dockerfile` | Python 3.13, entrypoint migrations |
| `docker-compose.yml` | Postgres, env vars |
| `pyproject.toml` | Deps async + auth |
| `app/core/domain/registry.py` | `get_cached_domain()` wrapper |
| `app/api/main.py` | Routers, lifespan, error handlers |
| `app/api/dependencies.py` | Async DB, auth, orchestrator por domínio |
| `app/agents/evaluator.py` | `EvaluationParseError` |
| `app/agents/orchestrator.py` | Remover prints (Fase 5) |
| `app/core/llm/config.py` | Redirect a settings unificado |
| `.github/workflows/ci.yml` | Postgres, migrations, tests/api |

---

## 13. Riscos conhecidos

| Risco | Mitigação |
|-------|-----------|
| Reidratação incorreta | Gate Fase 3 rigoroso |
| LLM dentro de transação | Spec explícita: LLM fora, persist depois |
| Cache quebra testes | `get_cached_domain` + `cache_clear` |
| Corrida dupla submit (D-07) | `UNIQUE(interview_id, turn_number)`; aceito v1 |
| Último submit lento (2 LLMs) | Documentar timeout; RNF-02 aceita sync |
| Migrate paralelo em réplicas | Fora de escopo v1 |
