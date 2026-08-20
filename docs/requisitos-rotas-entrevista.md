# Requisitos — Rotas FastAPI de Entrevistas (v1)

**Projeto:** interview-agent  
**Status:** Aprovado pelo usuário (decisões A-01 a A-12 e Q-01 a Q-05 fechadas)  
**Última atualização:** 2026-08-19

---

## 1. Contexto

Expor o fluxo já implementado em `OrchestratorAgent` via API HTTP REST, com:

- Autenticação bearer por usuário (registro + auth)
- Persistência Postgres (Alembic)
- Três rotas centrais de entrevista + rotas de suporte
- Feedback de avaliação oculto durante o fluxo; relatório final via `ReportingAgent`

### Estado atual do código

| Componente | Situação |
|---|---|
| `OrchestratorAgent` | `start()`, `submit_answer()`, `get_report()` — pronto |
| `InterviewState` | Dataclass em memória; persistência a implementar |
| API | Apenas `/health` e `/topics` |
| Auth / Postgres | Não implementados |
| Testes HTTP | Ausentes |

---

## 2. Decisões de produto (fechadas)

| ID | Decisão |
|---|---|
| **D-01** | Auth bearer **por usuário**, com **registro e login** (não mapa estático de tokens) |
| **D-02** | `/topics` (e `/domains`) podem ser **públicas** — escolher o mais simples na implementação |
| **D-03** | Relatório final = saída do `ReportingAgent` (`CandidateReport` agregado) |
| **D-04** | Falha de LLM em `submit_answer` → **503**; turno **não** persistido; candidato retoma depois |
| **D-05** | Persistir `Evaluation.raw_response` (provider, tokens, etc.) para observabilidade futura |
| **D-06** | `interview_id` exposto como **UUID** string |
| **D-07** | Sem lock de concorrência na v1; tratar em v2 |
| **D-08** | `/health` simples — apenas indica se o app está up (sem check de Postgres) |
| **D-09** | Dificuldade inicial default **1** (opcional no `POST /interviews`) |
| **D-10** | Mensagens de erro em **PT**; incluir campo **`code`** machine-readable |
| **D-11** | Tabela **`candidates`** explícita no Postgres |
| **D-12** | **Alembic** para migrations |
| **D-13** | Sem rotas `/questions` — pergunta vem em `current_question` nas respostas da entrevista |
| **D-14** | Sem rate limit na v1 |
| **D-15** | Um candidato não pode ter múltiplas entrevistas **ativas** simultaneamente |
| **D-16** | Domínio escolhido no `POST /interviews`; imutável na v1; troca mid-session é **futuro** |
| **D-17** | Cliente **não** recebe `level` nem `feedback` após cada resposta |
| **D-18** | Token **opaco** persistido em `auth_tokens` (não JWT na v1) |
| **D-19** | **Auto-registro** aberto; campos: `email` + `password` apenas |
| **D-20** | TTL do token: **24 horas**; sem refresh na v1 |
| **D-21** | Retomada de sessão via **`GET /interviews/active`** apenas (sem `GET /interviews/{id}` na v1) |
| **D-22** | Senha armazenada com hash (**bcrypt** ou **argon2**) — nunca em texto plano |

---

## 3. Rotas da API

### 3.1 Inventário completo (v1)

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| `GET` | `/health` | Pública | App está up |
| `GET` | `/domains` | Pública* | Lista domínios registrados |
| `GET` | `/topics?domain={domain}` | Pública* | Lista tópicos do domínio |
| `POST` | `/auth/register` | Pública | Registro de candidato |
| `POST` | `/auth/login` | Pública | Login → retorna bearer token |
| `POST` | `/interviews` | Bearer | Inicia entrevista |
| `GET` | `/interviews/active` | Bearer | Retoma entrevista ativa do candidato |
| `POST` | `/interviews/{id}/answers` | Bearer | Submete resposta |
| `GET` | `/interviews/{id}/report` | Bearer | Relatório final |

\* Públicas por decisão D-02 (simplicidade). Podem exigir bearer se implementação alternativa for mais simples.

### 3.2 Rotas explicitamente fora de escopo v1

- `/questions` (qualquer variante) — perguntas não são recurso REST
- `GET /interviews/{id}` — consulta por ID (v2; v1 usa apenas `/interviews/active`)
- `POST /interviews/{id}/abandon` — encerramento antecipado
- Rate limiting
- Troca de domínio mid-session
- Endpoint admin de listagem de entrevistas de terceiros

### 3.3 Fluxo do frontend

```
GET /domains → GET /topics?domain=… → POST /auth/login (ou register)
→ POST /interviews → loop POST /answers até finished=true → GET /report
```

Retomada após refresh: `GET /interviews/active`.

---

## 4. Requisitos funcionais

### Auth e candidatos

**RF-01 — Registro de candidato**  
`POST /auth/register` com `email` e `password`. Auto-registro aberto.  
Email duplicado → `409`. Senha persistida apenas como hash (bcrypt ou argon2).

**RF-02 — Login**  
`POST /auth/login` valida credenciais e retorna token bearer opaco associado ao `candidate_id`.  
Credenciais inválidas → `401`. Token gravado em `auth_tokens` com `expires_at` = now + 24h.

**RF-03 — Autenticação bearer**  
Rotas de entrevista exigem `Authorization: Bearer <token>`.  
Token ausente, inválido ou expirado → `401`.

**RF-04 — Identidade e ownership**  
Token mapeia para um `candidate_id`. Candidato A não acessa entrevista de B → `404`.

### Descoberta (pré-entrevista)

**RF-05 — Listar domínios**  
`GET /domains` retorna domínios do registry (`DomainEnum`).

**RF-06 — Listar tópicos**  
`GET /topics?domain={domain}` retorna tópicos do `question_bank`. Domínio inválido → `400`.

### Entrevista

**RF-07 — Iniciar entrevista**  
`POST /interviews` com `domain`, `topic`, `difficulty` (opcional, default 1).  
Retorna `201` com `interview_id` (UUID), `current_question`, `finished=false`.  
Se já existe entrevista ativa → `409`.

**RF-08 — Retomar entrevista ativa**  
`GET /interviews/active` retorna entrevista com `status=active` do candidato, incluindo `current_question` e contadores.  
Sem entrevista ativa → `404`.

**RF-09 — Submeter resposta**  
`POST /interviews/{id}/answers` com `answer` (não vazio).  
Resposta **não** inclui `level`, `feedback` nem dados de avaliação.  
Avaliação persistida internamente em `interview_turns`.  
Entrevista já finalizada → `409`. Answer vazio → `422`.

**RF-10 — Falha de LLM**  
Erro do provider durante avaliação → `503`; turno **não** gravado; estado da entrevista inalterado.

**RF-11 — Obter relatório**  
`GET /interviews/{id}/report` quando `finished=true`.  
Retorna `CandidateReport` do `ReportingAgent`.  
Entrevista em andamento → `409`. Segunda chamada reutiliza relatório persistido.

**RF-12 — Encerramento automático**  
Regras do orquestrador (máx. 10 perguntas, sem próxima pergunta, selector sem tópicos) refletidas na API.

**RF-13 — Uma entrevista ativa por candidato**  
Constraint no banco: `UNIQUE (candidate_id) WHERE status = 'active'`.

### Persistência e integração

**RF-14 — Persistência de sessão**  
Estado sobrevive a restart; reidratação produz `InterviewState` equivalente para o orquestrador.

**RF-15 — Persistência de observabilidade**  
`evaluation_provider`, `evaluation_model`, metadados de `raw_response` gravados em `interview_turns`.

**RF-16 — Integração com orquestrador**  
DI resolve `OrchestratorAgent` pelo domínio da sessão (não domínio fixo global).

**RF-17 — Migrations**  
Schema versionado com Alembic; Postgres no `docker-compose`.

**RF-18 — Testes HTTP**  
Fluxo completo com LLM mockado; cenários de erro (401, 404, 409, 422, 503).

---

## 5. Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | JSON, snake_case |
| RNF-02 | `submit_answer` síncrono (aguarda LLM) na v1 |
| RNF-03 | Transação DB por `submit_answer` (histórico + sessão) |
| RNF-04 | Tokens nunca logados; sem stack trace em produção |
| RNF-05 | Logs com `interview_id`, `candidate_id` (sem PII de respostas em info) |
| RNF-06 | `domain` extensível sem migration destrutiva |
| RNF-07 | Camadas HTTP / repositório / orquestrador testáveis separadamente |
| RNF-08 | Erros com `detail` (PT) + `code` machine-readable |
| RNF-09 | Interface `TokenValidator` extensível para evoluir auth sem mudar handlers |

---

## 6. Modelo de dados (Postgres)

### Entidades

```
candidates
├── id (UUID, PK)
├── email (unique, not null)
├── password_hash (not null)
├── created_at

interviews
├── id (UUID, PK)
├── candidate_id (FK → candidates)
├── domain (varchar)
├── status ('active' | 'finished')
├── topic, difficulty
├── current_question_* (snapshot: id, topic, difficulty, prompt)
├── questions_answered (int)
├── created_at, updated_at, finished_at
└── UNIQUE (candidate_id) WHERE status = 'active'

interview_turns
├── id (PK)
├── interview_id (FK)
├── turn_number
├── question_* (snapshot)
├── answer_text
├── evaluation_level, evaluation_feedback
├── evaluation_provider, evaluation_model
├── evaluation_raw_response (JSONB)
├── created_at

interview_reports
├── interview_id (PK, FK)
├── overall_summary, strengths, weaknesses, suggestions (JSONB arrays onde aplicável)
├── total_questions
├── generated_at

auth_tokens
├── id (PK)
├── token_hash (unique, not null) — token opaco nunca armazenado em texto plano
├── candidate_id (FK → candidates)
├── expires_at (not null, default now + 24h)
├── created_at
```

### Estados

```
[*] → active (POST /interviews)
active → active (POST /answers, ainda há perguntas)
active → finished (POST /answers, orquestrador encerra)
finished → finished (GET /report, idempotente)
```

---

## 7. Contratos API (resumo)

### Erro padrão

```json
{
  "detail": "Mensagem legível em português",
  "code": "INTERVIEW_ALREADY_FINISHED"
}
```

### `POST /auth/register` — request

```json
{
  "email": "candidato@example.com",
  "password": "senha-segura"
}
```

### `POST /auth/login` — response `200`

```json
{
  "access_token": "opaque-token-string",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### `GET /interviews/active` — response `200`

```json
{
  "interview_id": "550e8400-e29b-41d4-a716-446655440000",
  "domain": "async_messaging",
  "topic": "dead_letter_queue",
  "difficulty": 2,
  "finished": false,
  "questions_answered": 1,
  "current_question": {
    "id": "sqs-05",
    "topic": "dead_letter_queue",
    "difficulty": 2,
    "prompt": "..."
  }
}
```

### `POST /interviews` — request

```json
{
  "domain": "async_messaging",
  "topic": "dead_letter_queue",
  "difficulty": 1
}
```

### `POST /interviews/{id}/answers` — response (em andamento)

```json
{
  "interview_id": "550e8400-e29b-41d4-a716-446655440000",
  "finished": false,
  "questions_answered": 1,
  "topic": "dead_letter_queue",
  "difficulty": 2,
  "current_question": {
    "id": "sqs-05",
    "topic": "dead_letter_queue",
    "difficulty": 2,
    "prompt": "..."
  }
}
```

### `GET /interviews/{id}/report` — response

```json
{
  "interview_id": "550e8400-e29b-41d4-a716-446655440000",
  "overall_summary": "...",
  "strengths": ["..."],
  "weaknesses": ["..."],
  "suggestions": ["..."],
  "total_questions": 3
}
```

---

## 8. Escopo v1 vs futuro

| v1 | Futuro |
|---|---|
| Auth register/login + token opaco (24h TTL) | JWT, refresh tokens, OAuth |
| `GET /interviews/active` | `GET /interviews/{id}` |
| Domínio fixo por entrevista | Troca de domínio mid-session |
| Sem lock de concorrência | Lock otimista / version column |
| `/health` simples | `/health/ready` com Postgres |
| Relatório agregado (`CandidateReport`) | Breakdown pergunta a pergunta na API |
| Sem abandon endpoint | Encerramento antecipado |
| Sem rate limit | Rate limiting |

---

## 9. Decisões de auth (Q-01 a Q-05 — fechadas)

| ID | Decisão |
|---|---|
| **Q-01** | Token **opaco** persistido em `auth_tokens` (não JWT) |
| **Q-02** | **Auto-registro**; campos: `email` + `password` |
| **Q-03** | TTL **24 horas**; sem refresh na v1 |
| **Q-04** | Apenas **`GET /interviews/active`** (sem `GET /interviews/{id}`) |
| **Q-05** | Senha sempre **criptografada** (hash bcrypt ou argon2) |

---

## 10. Critérios de aceite globais

- [ ] `docker compose up` sobe API + Postgres + Qdrant
- [ ] Migrations aplicáveis do zero
- [ ] Candidato registra, loga, inicia entrevista, responde até fim, obtém relatório
- [ ] Segunda entrevista ativa simultânea → `409`
- [ ] Respostas de `submit_answer` nunca contêm `level`/`feedback`
- [ ] Falha LLM → `503` sem alterar estado persistido
- [ ] Refresh da página recupera entrevista em andamento
- [ ] Testes HTTP cobrem happy path e erros principais
