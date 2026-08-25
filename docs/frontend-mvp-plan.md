# Frontend MVP — Plano de Execução


| Campo       | Valor                                                     |
| ----------- | --------------------------------------------------------- |
| **Versão**  | 1.3                                                       |
| **Data**    | 2026-08-25                                                |
| **Perfil**  | Perfil 2 + Tailwind                                       |
| **Stack**   | React 19, Vite, TypeScript, Tailwind CSS, React Router v7 |
| **Backend** | FastAPI (`interview-agent` API existente)                 |


---

## Visão geral

SPA separada em `frontend/` para candidatos praticarem entrevistas técnicas: **registro → login → setup (domínio/tópico/dificuldade) → entrevista → relatório final**.

### Decisões de produto

- React Router para navegação multi-página
- Tailwind CSS para estilos
- Proxy Vite em dev + CORS no backend em prod
- Banner "Retomar entrevista" quando `GET /interviews/active` retorna 200 (sem auto-redirect)
- Com entrevista ativa: botão "Iniciar" **desabilitado**; retomar **somente** via Banner (sem auto-redirect)
- Token bearer em `localStorage` via abstração `authStorage`
- Pós-registro → redirect para login (sem auto-login)
- 401 → limpar token + redirect login + sync entre abas (`storage` event)
- `GET /active` antes de criar entrevista é otimização UX; em 409 `ACTIVE_INTERVIEW_EXISTS` **obrigatoriamente** re-fetch `GET /active` para obter `interview_id` (body do 409 não inclui id)
- Labels Fase 1: valores crus de domain/topic OK; dificuldade exibida inline como "Nível {n}"; humanização completa na Fase 2 (`humanize.ts`)
- Nomenclatura API/rota: campo `interview_id` em `InterviewResponse`; param de rota `:interviewId`
- Polling em respostas 503 (`LLM_UNAVAILABLE`) com backoff + retry manual
- Timeout de request: 60s
- Rascunho de resposta em `sessionStorage` (por `interviewId`)
- UI em PT-BR fixo; baseline de acessibilidade incremental

### API backend (referência)


| Método | Endpoint                   | Auth   | Notas                                                                     |
| ------ | -------------------------- | ------ | ------------------------------------------------------------------------- |
| POST   | `/auth/register`           | Não    | 409 `EMAIL_ALREADY_REGISTERED`                                            |
| POST   | `/auth/login`              | Não    | Retorna `access_token`, `expires_in`                                      |
| GET    | `/domains`                 | Não    | Lista domínios                                                            |
| GET    | `/topics?domain=`          | Não    | Tópicos por domínio                                                       |
| POST   | `/interviews`              | Bearer | 409 `ACTIVE_INTERVIEW_EXISTS` (body: `detail`+`code` apenas, **sem** `interview_id`), 503 `RAG_NOT_READY` |
| GET    | `/interviews/active`       | Bearer | 404 `NO_ACTIVE_INTERVIEW` → tratar como `null`                            |
| POST   | `/interviews/{id}/answers` | Bearer | 409 `DUPLICATE_TURN`, `INTERVIEW_ALREADY_FINISHED`; 503 `LLM_UNAVAILABLE` |
| GET    | `/interviews/{id}/report`  | Bearer | 409 `INTERVIEW_NOT_FINISHED`; 404 `INTERVIEW_NOT_FOUND`                   |


Respostas de erro: `{ "detail": string, "code": string }`.

**Nota:** não existe `GET /interviews/{id}` nem endpoint de cancelamento de entrevista ativa.

### Estrutura de pastas

```
frontend/
├── package.json
├── vite.config.ts          # proxy /api → backend em dev
├── tsconfig.json
├── tailwind.config.ts
├── index.html
└── src/
    ├── main.tsx            # ApiClientProvider (sem RouterProvider na Fase 1)
    ├── App.tsx
    ├── constants.ts        # MAX_ANSWER_LENGTH = 4096
    ├── config/
    │   └── env.ts          # VITE_API_BASE_URL
    ├── api/
    │   ├── client.ts       # createApiClient({ getToken, onUnauthorized })
    │   ├── types.ts
    │   └── endpoints/
    │       ├── auth.ts
    │       ├── interviews.ts
    │       └── discovery.ts
    ├── auth/
    │   └── authStorage.ts
    ├── components/
    │   ├── guards/
    │   │   ├── GuestRoute.tsx
    │   │   ├── RequireAuth.tsx
    │   │   ├── InterviewRouteGuard.tsx
    │   │   └── ReportRouteGuard.tsx
    │   ├── layout/
    │   │   ├── AppShell.tsx
    │   │   └── Header.tsx
    │   └── ui/
    │       ├── Button.tsx
    │       ├── Input.tsx
    │       ├── Select.tsx
    │       ├── Textarea.tsx
    │       ├── Banner.tsx
    │       ├── Spinner.tsx
    │       └── ErrorAlert.tsx
    ├── pages/
    │   ├── LoginPage.tsx
    │   ├── RegisterPage.tsx
    │   ├── SetupPage.tsx
    │   ├── InterviewPage.tsx
    │   └── ReportPage.tsx
    ├── hooks/
    │   ├── useActiveInterview.ts
    │   ├── useAnswerDraft.ts
    │   └── useReportPolling.ts
    ├── lib/
    │   ├── errorMapper.ts
    │   ├── humanize.ts
    │   └── backoff.ts
    └── routes.tsx
```

---

## Pré-requisitos

- [ ] Node.js 20+ e npm instalados
- [ ] Backend rodando localmente (`uv run uvicorn app.api.main:app --reload`)
- [ ] Postgres + Qdrant seedados (`docker compose up`, `uv run python scripts/run_seed.py`)
- [ ] Variáveis: `GROQ_API_KEY`, `OPENROUTER_API_KEY` no `.env` do backend

---

## Fase 1 — Fundação e fluxo feliz

**Objetivo:** fluxo completo funcionando localmente com guards corretos por rota.

### Backend

- [x] **1.0 CORS** — Em `app/core/settings.py`, adicionar `CORS_ORIGINS: list[str]` (default `["http://localhost:5173", "http://127.0.0.1:5173"]`). Em `app/api/main.py`, registrar `CORSMiddleware` (`allow_credentials=False`, methods `GET/POST/OPTIONS`, headers `Authorization`/`Content-Type`). Teste API: preflight e request com `Origin` permitido retornam headers CORS.
  - **Pronto quando:** teste API passa; browser em `localhost:5173` consegue chamar API.

### Scaffold e config

- [x] **1.1 Scaffold** — Criar `frontend/` com Vite + React + TS. Instalar: `react-router-dom`, `tailwindcss`, `@tailwindcss/vite`. Configurar proxy em `vite.config.ts` para `/auth`, `/domains`, `/topics`, `/interviews`, `/health` → `http://localhost:8000`.
  - **Pronto quando:** `npm run dev` abre app em `:5173`.

- [x] **1.1b .gitignore** — Adicionar ao `.gitignore` raiz: `node_modules/`, `frontend/dist/`, `.env.local`, `frontend/.env.local`.
  - **Pronto quando:** `git status` não lista `node_modules` nem `dist`.

- [x] **1.2 constants.ts** — Criar `frontend/src/constants.ts` com `export const MAX_ANSWER_LENGTH = 4096` (espelha `app/core/constants.py`).
  - **Pronto quando:** importado na página de entrevista.

- [x] **1.2b env.ts** — `frontend/src/config/env.ts`: `export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''` (proxy relativo em dev).
  - **Pronto quando:** client usa essa constante.

### API client (DI)

- [x] **1.3 client.ts** — Implementar factory com injeção de dependências:
  ```ts
  export type ApiClientConfig = {
    getToken: () => string | null;
    onUnauthorized: () => void;
  };
  export function createApiClient(config: ApiClientConfig) { ... }
  ```
  - Fetch wrapper com JSON, `Authorization: Bearer`, parse de `{ detail, code }` em erros.
  - Se status 401 → chamar `onUnauthorized()` antes de propagar erro.
  - `getActiveInterview()`: 404 `NO_ACTIVE_INTERVIEW` → retorna `null` (não lança erro).
  - **Pronto quando:** sem imports de `authStorage` dentro de `client.ts` (DI pura).

- [x] **1.3b endpoints/** — `auth.ts` (register, login), `discovery.ts` (domains, topics), `interviews.ts` (start, active, submitAnswer, getReport).
  - **Pronto quando:** tipos TypeScript espelham schemas Pydantic.

- [x] **1.3c main.tsx** — Instanciar client e prover via React Context (`ApiClientProvider`). **Sem** `RouterProvider` — routing fica em `App.tsx` (Fase 1) até migração em 1.9:
  ```ts
  const apiClient = createApiClient({
    getToken: () => authStorage.getToken(),
    onUnauthorized: () => { authStorage.clear(); window.location.href = '/login'; },
  });
  ```
  - **Pronto quando:** nenhum import circular entre `authStorage` ↔ `client`.

### Autenticação

- [x] **1.4 authStorage.ts** — `getToken()`, `setToken(token)`, `clear()`, `onChange(callback)` para sync entre abas.
  - **Pronto quando:** persiste em `localStorage`; evento `storage` propagado.

- [x] **1.4b LoginPage** — Form email/senha → `POST /auth/login` → salvar token → redirect `/`.
  - Erros: `INVALID_CREDENTIALS` → mensagem amigável.

- [x] **1.4c RegisterPage** — Form → `POST /auth/register` → redirect `/login?registered=1` com mensagem "Conta criada".
  - Erro `EMAIL_ALREADY_REGISTERED` → mensagem específica.

- [x] **1.4d RequireAuth** — Layout route com `<Outlet />`. Se sem token → `<Navigate to="/login" />`.
  - **Pronto quando:** `/` inacessível sem login.

- [x] **1.4e GuestRoute** — Layout route com `<Outlet />` (já implementado). Se autenticado → redirect `/`.
  - Usado em `/login` e `/register` via `App.tsx`.

### Layout

- [x] **1.5 AppShell** — Header com título, botão Sair (clear + `/login`), `<Outlet />`.
  - **Pronto quando:** todas as páginas autenticadas usam shell.

### Política UI (Fase 1)

| Escopo | Componentes | Notas |
| ------ | ----------- | ----- |
| **1.6a** (primitivos compartilhados) | `Banner`, `Select`, `Spinner`, `ErrorAlert`, `Button` | Usados em SetupPage, guards e páginas de fluxo |
| **1.7b** | `Textarea` | Criado junto com InterviewPage (não em 1.6a) |
| **Auth (Login/Register)** | Inline em páginas | **Não refatorar** para `components/ui/` na Fase 1 |

### Componentes UI e hook compartilhado

- [x] **1.6a Componentes UI mínimos** — Criar em `components/ui/`:
  - `Banner.tsx` — variante informativa com slot para link/ação (ex.: "Retomar entrevista")
  - `Select.tsx` — wrapper acessível (`<label>` + `<select>`) com props `value`, `onChange`, `options`, `disabled`, `placeholder`
  - `Spinner.tsx` — indicador de carregamento reutilizável
  - `ErrorAlert.tsx` — exibe mensagem de erro com `role="alert"`
  - `Button.tsx` — botão reutilizável com variantes mínimas (primary/disabled) e suporte a `isLoading`
  - **Por quê:** SetupPage e guards (1.7, 1.8) dependem desses primitivos; implementar antes evita duplicação.
  - **Não incluir:** `Textarea` (1.7b), `Input` (auth permanece inline).
  - **Pronto quando:** componentes renderizam isoladamente com props mínimas; usados em pelo menos uma tela.

- [x] **1.6c useActiveInterview** — Hook **sem Context** em `hooks/useActiveInterview.ts`:
  ```ts
  // Interface: { active, isLoading, error, refetch }
  // active: InterviewResponse | null (404 NO_ACTIVE_INTERVIEW → null, sem throw)
  // Delega fetch para apiClient.getActiveInterview()
  ```
  - Usado por SetupPage (Banner + desabilitar Iniciar) e InterviewRouteGuard (1.7).
  - **Não misturar** com loading de domains/topics — `useActiveInterview` cobre **somente** `GET /interviews/active`.
  - **Por quê:** evita duplicar lógica de active interview e garante comportamento consistente.
  - **Pronto quando:** hook retorna `null` em 404; propaga erros reais; `refetch` reutilizável após 409.

### Setup e banner

- [x] **1.6b SetupPage** — Substituir placeholder `Home` em `/` por `SetupPage.tsx`.

  **Ao montar (paralelo, estados separados):**
  1. `useActiveInterview()` — loading/erro de entrevista ativa (`isLoading`, `error`, `refetch`)
  2. Domains/topics — `useDomainTopics` **ou** lógica local na SetupPage (`isLoadingDomains`, `isLoadingTopics`, erros próprios); **não** via `useActiveInterview`
  3. `Spinner` enquanto qualquer fetch inicial pendente (domains, topics ou active)
  4. `ErrorAlert` em falhas de fetch (domains, topics ou active), cada fonte com mensagem adequada

  **Cascata domain → topics:**
  - Auto-selecionar **primeiro** domain ao carregar lista
  - Ao trocar domain: limpar topic selecionado → `GET /topics?domain=X` → auto-selecionar **primeiro** topic
  - **Stale guard:** abortar request anterior (`AbortController`) ou ignorar resposta com request id desatualizado
  - Empty states: mensagem quando domains vazio ou topics vazio para domain selecionado

  **Select dificuldade:** 1–5 (default 1), label inline **"Nível {n}"** (sem `humanize.ts` na Fase 1)

  **Entrevista ativa (`useActiveInterview`):**
  - Se `active !== null`: exibir `Banner` "Você tem uma entrevista em andamento" com link `/interview/{active.interview_id}`
  - Botão **"Iniciar" desabilitado** quando `active !== null` (retomar somente via Banner)
  - Sem auto-redirect ao detectar active

  **Botão "Iniciar" (`isSubmitting` durante POST):**
  1. UX: se `active !== null` → botão já desabilitado (passo acima)
  2. `POST /interviews` com `{ domain, topic, difficulty }`
  3. Sucesso → redirect `/interview/{response.interview_id}`
  4. **409 `ACTIVE_INTERVIEW_EXISTS`:** body tem apenas `{ detail, code }` — **obrigatoriamente** chamar `refetch()` / `getActiveInterview()`:
     - Se retornar active → exibir Banner com link `/interview/{active.interview_id}` (e manter Iniciar desabilitado)
     - Se retornar `null` (TOCTOU race) → `ErrorAlert` com mensagem genérica ("Já existe uma entrevista ativa, mas não foi possível recuperá-la. Tente novamente.")
  5. **503 `RAG_NOT_READY`:** `ErrorAlert` com orientação de seed

  **Nota TOCTOU:** `GET /active` antes do POST é otimização UX (desabilitar Iniciar cedo); o caminho **obrigatório** em corrida é 409 → re-fetch active.

  - **Pronto quando (1.6b parcial):** selects funcionam, Banner aparece, Iniciar desabilitado com active, redirect pós-POST funciona, 409+re-fetch tratado.
  - **Pronto quando (SetupPage navegável):** inclui 1.6a + 1.6c + 1.9a (links do Banner e redirect pós-POST abrem stubs) + fluxo feliz iniciar/retomar.

### Entrevista

- [x] **1.7 InterviewRouteGuard** — **Layout route** com `<Outlet />` (mesmo padrão de `RequireAuth` / `GuestRoute`). Lógica (enquanto loading, mostrar `Spinner` via `useActiveInterview`):

  **Nota arquitetural:** extrair decisão de rota em função pura `resolveInterviewRoute(active, interviewId, reportStatus)` em `lib/` ou junto ao guard — facilita testes e evita lógica duplicada.

  | Passo | Condição                                              | Ação                                                          |
  | ----- | ----------------------------------------------------- | ------------------------------------------------------------- |
  | 1     | Sem token                                             | RequireAuth → login                                           |
  | 2     | `GET /active` 200 e `interview_id === :interviewId`   | Renderizar `<InterviewPage />`                                |
  | 3     | `GET /active` 200 e `interview_id !== :interviewId`   | Redirect `/interview/{active.interview_id}`                   |
  | 4     | 404 `NO_ACTIVE_INTERVIEW`                             | `GET /report/:interviewId`                                    |
  | 4a    | report 200                                            | Redirect `/report/:interviewId` (deep link pós-finalização)  |
  | 4b    | report falha                                          | Redirect `/`                                                  |
  | 5     | Outro erro                                            | `ErrorAlert` + link setup                                     |

  - Comparar sempre `InterviewResponse.interview_id` com param de rota `:interviewId`.
  - **Pronto quando:** refresh em entrevista ativa funciona; refresh após submit final vai para report.

- [x] **1.7b InterviewPage** — Criar `Textarea.tsx` em `components/ui/` e usar na página. Exibir `current_question.prompt`, textarea (max `MAX_ANSWER_LENGTH`), contador de caracteres, progresso `questions_answered`/10, botão Enviar (`Button` de 1.6a).
  - Mount: estado vem de `GET /active` (via guard); validar `current_question.id`
  - **Rascunho (draft):** Fase 2 — `2.5 useAnswerDraft` (não implementar restauração de draft na Fase 1)
  - Submit → `POST /interviews/{interviewId}/answers`
  - Se `finished: true` → redirect `/report/{interviewId}`
  - Senão → atualizar pergunta na UI
  - **Pronto quando:** fluxo de múltiplas perguntas funciona.

### Relatório

- [x] **1.8 ReportRouteGuard** — **Layout route** com `<Outlet />`. `GET /interviews/:interviewId/report`:

  | Status | Código                   | Ação                                                       |
  | ------ | ------------------------ | ---------------------------------------------------------- |
  | 200    | —                        | Renderizar `<ReportPage />`                                |
  | 404    | `INTERVIEW_NOT_FOUND`    | Redirect `/`                                               |
  | 409    | `INTERVIEW_NOT_FINISHED` | Redirect `/interview/:interviewId`                         |
  | 503    | `LLM_UNAVAILABLE`        | Mensagem + botão retry manual (polling completo na Fase 2) |


- [x] **1.8b ReportPage** — Exibir `overall_summary`, listas `strengths`, `weaknesses`, `suggestions`, `total_questions`. Botão "Nova entrevista" → `/`.
  - **Pronto quando:** report legível após entrevista; deep link `/report/:interviewId` funciona.

### Rotas

**Fase 1 (até 1.9):** rotas definidas em `App.tsx` com `BrowserRouter` (como no código atual). `main.tsx` provê apenas `ApiClientProvider` — **não** `RouterProvider`.

- [x] **1.9a Rotas stub (simétricas)** — Registrar em `App.tsx` **antes** de SetupPage navegável:
  ```
  /interview/:interviewId → RequireAuth > AppShell > placeholder ("Entrevista em construção")
  /report/:interviewId    → RequireAuth > AppShell > placeholder ("Relatório em construção")
  ```
  - **Por quê:** Banner, redirect pós-POST e deep links precisam de destinos navegáveis antes dos guards reais (1.7, 1.8).
  - **Pronto quando:** link do Banner, redirect após `POST /interviews` e navegação manual a `/report/:id` abrem stubs sem 404.

- [ ] **1.9 routes.tsx** — Migração incremental: mover definição de rotas de `App.tsx` para `routes.tsx` e substituir stubs 1.9a pelos guards reais (após 1.7 + 1.8):
  ```
  /login                    → GuestRoute > LoginPage
  /register                 → GuestRoute > RegisterPage
  /                         → RequireAuth > AppShell > SetupPage
  /interview/:interviewId   → RequireAuth > AppShell > InterviewRouteGuard
  /report/:interviewId      → RequireAuth > AppShell > ReportRouteGuard
  ```
  - `GuestRoute` (existente): redirect `/` se autenticado — usado em login/register
  - `RequireAuth`: layout route com `<Outlet />` — token obrigatório
  - Guards (`InterviewRouteGuard`, `ReportRouteGuard`): layout routes com `<Outlet />`
  - Param de rota `:interviewId` mapeia para `InterviewResponse.interview_id`
  - **Pronto quando:** matriz de guards respeitada; stubs 1.9a substituídos por guards reais; `App.tsx` delega a `routes.tsx`.

- [ ] **1.10 Smoke manual** — Executar fluxo completo + refresh em cada URL.
  - **Pronto quando:** checklist Fase 1 (abaixo) 100%.

---

## Fase 2 — Resiliência, erros e deploy

**Objetivo:** produção confiável com tratamento de erros, CI e deploy.

- [ ] **2.1 errorMapper.ts** — Mapa `code → string` PT-BR para todos os códigos de `app/core/exceptions.py` + `VALIDATION_ERROR`. HTTP 429 → "Muitas requisições. Tente novamente em instantes." (backlog rate limit backend).
  - **Pronto quando:** todas as telas usam `errorMapper`.

- [ ] **2.2 Polling 503** — Hook `useReportPolling`: retry exponencial (2s, 4s, 8s, 16s, cap 30s) **somente** em `LLM_UNAVAILABLE`. Não poll em `409 INTERVIEW_NOT_FINISHED`.
  - **Pronto quando:** report pós-finalização com delay mostra "Gerando relatório…" e recupera.

- [ ] **2.3 Timeout 60s** — `AbortController` no client; abort → "A requisição demorou demais. Tente novamente." Diferenciar timeout de rede vs 503.
  - **Pronto quando:** request travada não bloqueia UI indefinidamente.

- [ ] **2.4 DUPLICATE_TURN** — Em 409 `DUPLICATE_TURN` no submit: desabilitar botão, re-fetch `GET /active`, sincronizar estado.
  - **Pronto quando:** double-click em Enviar não corrompe estado.

- [ ] **2.5 useAnswerDraft** — `sessionStorage` chave `interview_draft_{interviewId}` com `{ questionId, answer }`; debounce 300ms; restaurar ao montar; limpar após submit 200 ou `finished`.
  - **Pronto quando:** refresh durante resposta preserva texto; troca de pergunta descarta draft antigo.

- [ ] **2.6 Loading UX** — Spinner + "Avaliando resposta…", botão disabled, `aria-busy="true"` durante submit.
  - **Pronto quando:** sem double-submit; UX clara em espera.

- [ ] **2.7 humanize.ts + labels.ts** — `humanizeDomain()`, `humanizeTopic()`, `difficultyLabel(n)` com mapa estático PT-BR + fallback.
  - **Pronto quando:** setup e entrevista exibem nomes legíveis.

- [ ] **2.8 CI frontend** — Em `.github/workflows/ci.yml`, job `frontend`: `npm ci`, `npm run build`, `npm test` em `frontend/`.
  - **Pronto quando:** PR com mudança em `frontend/` dispara build.

- [ ] **2.9 Deploy** — Frontend: build estático com `VITE_API_BASE_URL`. Backend: `CORS_ORIGINS` com URL de prod. Documentar workflow dev no README.
  - **Pronto quando:** fluxo completo em URL pública.

- [ ] **2.10 Testes unitários** — Vitest: `errorMapper`, `authStorage`, `getActiveInterview` (404→null), `useReportPolling` (só 503). Mínimo 5 testes.
  - **Pronto quando:** `npm test` verde no CI.

---

## Fase 3 — Polish e aceite

**Objetivo:** qualidade para primeiros usuários externos.

- [ ] **3.1** — Commitar `package-lock.json`; pin versões React 19 / Router 7.
- [ ] **3.2** — Validação client-side: email formato, senha 8–128 chars, resposta não vazia/whitespace, `answer.length <= MAX_ANSWER_LENGTH`.
- [ ] **3.3** — A11y incremental: `<label>` em inputs, foco visível (`focus-visible:ring-2`), `aria-live="polite"` em erros, navegação por teclado, `role="progressbar"` no indicador.
- [ ] **3.4** — Modal `<dialog>` nativo: confirmar ao sair com draft não vazio.
- [ ] **3.5** — Polish visual Tailwind: espaçamento, tipografia, estados hover/focus/disabled consistentes.
- [ ] **3.6** — Atualizar `docs/product_roadmap.md` e README com seção "Frontend local dev".
- [ ] **3.7** — Aceite: 3–5 testadores completam fluxo sem assistência técnica.

---

## Critérios de aceite por fase

### Fase 1

- [ ] Register → login → setup → entrevista → report sem erros no fluxo feliz
- [ ] Banner de retomar aparece com entrevista ativa (sem auto-redirect)
- [ ] Refresh em `/interview/:interviewId` (ativa) mantém na entrevista
- [ ] Refresh em `/interview/:interviewId` (finalizada) redireciona para `/report/:interviewId`
- [ ] `/report/:interviewId` com entrevista em andamento redireciona para `/interview/:interviewId`
- [ ] Com entrevista ativa, botão "Iniciar" desabilitado; retomar só via Banner
- [ ] 409 `ACTIVE_INTERVIEW_EXISTS` seguido de re-fetch `GET /active` monta link correto
- [ ] `GET /active` 404 tratado como null (sem toast de erro)
- [ ] Logout limpa token e bloqueia rotas protegidas
- [ ] 401 global limpa sessão e redireciona login
- [ ] CORS + proxy funcionam em dev (`localhost:5173`)

### Fase 2

- [ ] 503 em report faz polling automático com backoff
- [ ] Double-click submit tratado (`DUPLICATE_TURN`)
- [ ] Draft preservado em refresh; descartado ao mudar pergunta
- [ ] Todos error codes mapeados em PT-BR
- [ ] CI build + test frontend verde em PR
- [ ] Deploy prod funcional

### Fase 3

- [ ] Validações client-side impedem submit inválido
- [ ] A11y baseline verificada manualmente
- [ ] 3–5 testadores externos completam fluxo

---

## Matriz de guards


| Rota frontend              | Componente guard      | Verificações                                          |
| -------------------------- | --------------------- | ----------------------------------------------------- |
| `/login`, `/register`      | `GuestRoute`          | Redirect `/` se autenticado                           |
| `/`                        | `RequireAuth`         | Token presente                                        |
| `/interview/:interviewId`  | `InterviewRouteGuard` | Token + `GET /active` + match `interview_id` + fallback report |
| `/report/:interviewId`     | `ReportRouteGuard`    | Token + `GET /:interviewId/report` + redirect por status       |
| Futuras rotas autenticadas | `RequireAuth`         | Token presente                                        |


### Fluxo InterviewRouteGuard

```
GET /active
├── 200 + interview_id match     → InterviewPage
├── 200 + interview_id mismatch  → redirect /interview/{active.interview_id}
└── 404 NO_ACTIVE
    └── GET /report/:interviewId
        ├── 200 → redirect /report/:interviewId
        └── else → redirect /
```

### Fluxo ReportRouteGuard

```
GET /:interviewId/report
├── 200 → ReportPage
├── 404 → redirect /
├── 409 INTERVIEW_NOT_FINISHED → redirect /interview/:interviewId
└── 503 → polling (Fase 2) / retry manual (Fase 1)
```

### Fluxo SetupPage — 409 ACTIVE_INTERVIEW_EXISTS

```
POST /interviews
├── 200 → redirect /interview/{response.interview_id}
├── 409 ACTIVE_INTERVIEW_EXISTS
│   └── GET /active (obrigatório)
│       ├── 200 → Banner + link /interview/{active.interview_id}; Iniciar desabilitado
│       └── 404 → ErrorAlert genérico (TOCTOU race)
├── 503 RAG_NOT_READY → ErrorAlert com orientação de seed
└── outro → ErrorAlert
```

---

## Dependências entre etapas

```
1.0 CORS → 1.3 API client (dev cross-origin)
1.1 Scaffold → tudo frontend
1.3 API client → 1.4 Auth → 1.5 AppShell
1.5 AppShell → 1.6a UI → 1.6c useActiveInterview → 1.9a stubs → 1.6b SetupPage
1.6c useActiveInterview → 1.7 InterviewRouteGuard (hook compartilhado; só active)
1.9a stubs → 1.6b SetupPage (Banner/redirect/deep link navegáveis)
1.6b SetupPage → 1.7 Interview (domains/topics independentes de useActiveInterview)
1.2 constants → 1.7b InterviewPage (validação answer + Textarea)
1.7 Interview → 1.8 Report (fluxo feliz entrega interviewId ao report)
1.7 + 1.8 guards → 1.9 routes.tsx (migra App.tsx → routes.tsx; substitui stubs)
1.9 routes → 1.10 Smoke manual
2.8 CI → antes de 2.9 Deploy prod
Fase 1 completa → Fase 2 → Fase 3
```

### Ordem de execução recomendada (Fase 1 — pós-1.5)

1. **1.6a** — Componentes UI mínimos (Banner, Select, Spinner, ErrorAlert, Button)
2. **1.6c** — `useActiveInterview` hook (sem Context; só `GET /active`)
3. **1.9a** — Rotas stub simétricas (`/interview/:id`, `/report/:id`) em `App.tsx`
4. **1.6b** — SetupPage (domains/topics com loading separado; substitui `Home`)
5. **1.7** — InterviewRouteGuard + InterviewPage (+ Textarea em 1.7b)
6. **1.8** — ReportRouteGuard + ReportPage
7. **1.9** — Migração a `routes.tsx` + guards reais (substitui stubs 1.9a)
8. **1.10** — Smoke manual (checklist Fase 1)

---

## Riscos


| Risco                         | Impacto                            | Mitigação                                       |
| ----------------------------- | ---------------------------------- | ----------------------------------------------- |
| Latência LLM > 60s            | Submit/report falha                | Polling 503; mensagem clara; retry manual       |
| Sem rate limit no backend     | Abuso em auth                      | Mensagem 429 no frontend; backlog rate limit    |
| Token em localStorage         | XSS rouba sessão                   | MVP aceito; httpOnly cookies em versão futura   |
| CORS misconfiguration em prod | App quebrada                       | Testar preflight em staging; origens explícitas |
| Sem GET /interviews/{id}      | Guard depende de /active + /report | Matriz de guards por rota (incorporada)         |
| Deep link entrevista alheia   | 404 → home                         | API valida ownership por candidate_id           |


---

## Backlog (fora do MVP)

- Rate limiting real no backend (`429` em `/auth/login`, `/auth/register`)
- Histórico de entrevistas (`GET /interviews` lista)
- `GET /interviews/{id}` (metadados)
- httpOnly cookies
- SSE/streaming para progresso de avaliação
- E2E Playwright completo
- Gerar types TypeScript a partir de OpenAPI (`/openapi.json`)

---

## Referências

- Backend errors: `app/core/exceptions.py`, `app/api/errors.py`
- API routers: `app/api/routers/{auth,interviews,discovery}.py`
- Schemas: `app/api/schemas/{auth,interviews}.py`
- `MAX_ANSWER_LENGTH`: `app/core/constants.py` (4096)
- Product scope: `docs/product_roadmap.md` (v0.3)
- CORS pendente: `docs/todo.md`

