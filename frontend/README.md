# Interview Agent — Frontend

React SPA for the Interview Agent platform. Candidates register, log in, configure an interview (domain, topic, difficulty), answer questions, and view a structured report at the end.

UI copy is in **Portuguese**. API error messages may come from the backend in Portuguese as well.

## Stack

| Layer | Technology |
|-------|------------|
| UI | React 19, TypeScript |
| Build | Vite 8 |
| Routing | React Router 7 |
| Styling | Tailwind CSS 4 |
| Auth | Bearer token in `localStorage` (`interview-agent:access_token`) |

## Routes

| Path | Guard | Page |
|------|-------|------|
| `/login` | Guest only | Login |
| `/register` | Guest only | Register |
| `/` | Authenticated | Setup — choose domain, topic, difficulty; start or resume interview |
| `/interview/:interviewId` | Authenticated + active interview | Question screen and answer submit |
| `/report/:interviewId` | Authenticated + finished interview | Final report with retry on `LLM_UNAVAILABLE` |

Route guards live in `src/components/guards/`:

- `GuestRoute` — redirects authenticated users away from login/register
- `RequireAuth` — redirects to `/login` when token is missing or invalid
- `InterviewRouteGuard` — ensures the interview is active and belongs to the session
- `ReportRouteGuard` — loads report with loading/error/retry states

## Local development

Prerequisites: API running on `http://localhost:8000` (see root [README](../README.md)).

```bash
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies API paths to `:8000` (see `vite.config.ts`) — no `VITE_API_BASE_URL` needed locally.

### Environment

Copy [`.env.example`](.env.example):

```bash
cp .env.example .env
```

| Variable | Dev | Production |
|----------|-----|------------|
| `VITE_API_BASE_URL` | Leave empty (proxy) | Public API URL (e.g. Render) |

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server on `:5173` with HMR |
| `npm run build` | Typecheck + production bundle to `dist/` |
| `npm run preview` | Serve production build locally |
| `npm run lint` | ESLint |

## Project layout

```
src/
├── api/           # HTTP client, endpoints, types
├── auth/          # Token storage and auth sync hook
├── components/
│   ├── guards/    # Route guards
│   ├── layout/    # AppShell, Header
│   └── ui/        # Button, Spinner, ErrorAlert, etc.
├── config/        # env.ts (VITE_API_BASE_URL)
├── hooks/         # useActiveInterview
├── lib/           # Route resolution helpers
├── pages/         # Login, Register, Setup, Interview, Report
├── constants.ts   # MAX_ANSWER_LENGTH (4096), TOTAL_QUESTIONS (10)
├── routes.tsx
└── main.tsx
```

## Deploy (Vercel)

1. Connect the repo and set **Root Directory** to `frontend`.
2. Build command: `npm run build` (default).
3. Set environment variable `VITE_API_BASE_URL` to the production API URL.
4. Ensure the API has `CORS_ORIGINS` set to your Vercel URL.

[`vercel.json`](vercel.json) rewrites all paths to `index.html` for client-side routing.

## Interview flow (UI)

1. **Register** → redirect to login with `?registered=1`
2. **Login** → token stored in `localStorage` → `/`
3. **Setup** → pick domain, topic, difficulty → start interview
4. **Interview** → answer up to 10 questions → auto-navigate to report when finished
5. **Report** → view summary, strengths, weaknesses, suggestions; retry if LLM failed

If Qdrant is not seeded, setup shows a hint for `docker compose --profile seed run --rm seed`.

## Further reading

- Root [README](../README.md) — API, Docker, tests
- [infra/README.md](../infra/README.md) — production deploy (Render + Supabase + Qdrant Cloud)
- [CHANGELOG.md](../CHANGELOG.md) — release history
