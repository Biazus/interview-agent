# TODO — Dependency audit & follow-ups

Findings from the **dependencias-agent** review (post Fases 0–4).  
Severity: **High** · **Medium** · **Low** · **Info**

---

## Dependencies (`pyproject.toml`)

- [ ] **[High]** `pytest` is listed under runtime `dependencies` instead of dev.  
  **Recommendation:** Move `pytest` to `dependency-groups.dev` alongside `pytest-asyncio`. Production Docker uses `uv sync --frozen --no-dev` and should not install test tooling.

- [ ] **[High — deploy]** `sentence-transformers` pulls in `torch` (~500 MB+ on Linux), inflating Docker image size, cold start, and memory (~400 MB+ RAM typical).  
  **Recommendation:** Document the impact in README/deployment docs. For later scaling, consider alternatives: `fastembed` / ONNX, a hosted embedding API, or a dedicated sidecar service.

- [ ] **[Medium]** `python-dotenv` is declared as a direct runtime dependency but is not imported in application code.  
  **Recommendation:** Remove from `dependencies`; `pydantic-settings` already brings it in transitively for `env_file=".env"`.

- [ ] **[Low]** Pinning strategy is inconsistent: `ruff==0.6.1` is exact while most other packages use `>=`.  
  **Recommendation:** Document the intentional pin for reproducible CI, or align on a single strategy (pin all tooling or use compatible ranges).

- [ ] **[Low]** `uvicorn` is installed without the `[standard]` extra (no reload / websockets helpers out of the box).  
  **Recommendation:** Optional — add `uvicorn[standard]` for local dev if reload or WebSockets are needed; production may stay as-is.

- [ ] **[Low]** `[project.scripts] interview-agent = "interview_agent:main"` is configured while `package = false`, so the entry point is non-functional.  
  **Recommendation:** Remove the script entry until a real CLI exists, or fix packaging and implement `interview_agent:main`.

---

## Security & CI

- [ ] **[Info]** No automated CVE / vulnerability scan in CI.  
  **Recommendation:** Add a CI step (`uv export` + `pip-audit`) or enable Dependabot / GitHub Advisory monitoring; prioritize `fastapi`, `sqlalchemy`, `torch`, `pyyaml`, and `argon2-cffi`.

---

## Accepted as-is (no action required)

- `groq` + `openai` (two LLM SDKs) — justified by Groq → OpenRouter fallback chain.
- `openai` used only as OpenRouter HTTP adapter — mature SDK; replacing with raw `httpx` adds maintenance for little gain.
- `httpx` in dev only — correct; runtime receives it transitively via `qdrant-client` and `openai`.
- API / persistence stack (`fastapi`, `sqlalchemy`, `asyncpg`, `alembic`, `argon2-cffi`, `email-validator`, `pydantic-settings`) — appropriate for v1.
