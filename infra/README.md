# Infrastructure — interview-agent

Terraform configuration for production/demo deployment:

| Component | Provider | Role |
|-----------|----------|------|
| API | [Render](https://render.com) | Docker web service (FastAPI) |
| Database | [Supabase](https://supabase.com) | Existing Postgres project (referenced, not created) |
| Vectors | [Qdrant Cloud](https://cloud.qdrant.io) | Existing cluster (referenced, not created) |
| Frontend | [Vercel](https://vercel.com) | Manual setup — not managed by Terraform |

## Prerequisites

- [Terraform](https://www.terraform.io/) ≥ 1.7.0
- Render account with API key and owner ID
- Existing Supabase project (Postgres connection string)
- Existing Qdrant Cloud cluster (endpoint + API key)
- Groq and OpenRouter API keys

### Environment variables (not in `.tfvars`)

| Variable | Where to get it |
|----------|-----------------|
| `RENDER_API_KEY` | Render Dashboard → Account Settings → API Keys |
| `RENDER_OWNER_ID` | Render Settings — `usr-...` or `tea-...` |

Set locally before `terraform plan/apply`, or in GitHub Actions secrets if using CI (workflow is currently commented out in `.github/workflows/terraform.yml`).

Sensitive Terraform variables can also be passed as `TF_VAR_*` environment variables instead of writing them in `terraform.tfvars`.

## Quick start

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — fill github_repo_url, cors_origins, database_url, API keys, Qdrant cluster details

export RENDER_API_KEY="rnd_..."
export RENDER_OWNER_ID="usr_..."

terraform init
terraform plan
terraform apply
```

**Do not commit `terraform.tfvars`** — it contains secrets. The file is gitignored.

## Variables

See [`terraform.tfvars.example`](terraform.tfvars.example) and [`variables.tf`](variables.tf).

| Variable | Description |
|----------|-------------|
| `github_repo_url` | HTTPS repo URL for Render auto-deploy |
| `cors_origins` | Frontend origin(s) allowed by the API (comma-separated if multiple) |
| `supabase_project_ref` | Supabase project ref (documentation/reference) |
| `database_url` | Postgres URI (`postgresql://` or `postgresql+asyncpg://`; SSL required for Supabase) |
| `qdrant_cluster_id` | Qdrant cluster UUID (reference only) |
| `qdrant_cluster_endpoint` | Qdrant Cloud HTTPS URL |
| `qdrant_cluster_api_key` | Qdrant database API key |
| `groq_api_key` | Groq LLM key |
| `openrouter_api_key` | OpenRouter fallback key |
| `render_plan` | Render plan (`free` default; `starter+` avoids cold start) |

## Outputs

After `terraform apply`:

| Output | Use |
|--------|-----|
| `api_url` | Public API base URL |
| `vercel_hint` | Suggested `VITE_API_BASE_URL=...` for Vercel |
| `supabase_project_ref` | Dashboard link reference |
| `qdrant_cluster_url` | Qdrant endpoint reference |

```bash
terraform output api_url
terraform output vercel_hint
```

## Post-deploy checklist

### 1. Configure Vercel (frontend)

1. Connect repo, root directory `frontend`.
2. Set `VITE_API_BASE_URL` to `terraform output -raw api_url`.
3. Deploy — note the Vercel URL.

### 2. Align CORS

Ensure `cors_origins` in `terraform.tfvars` matches the Vercel URL, then re-apply if you changed it:

```bash
terraform apply
```

Render redeploys the API with updated `CORS_ORIGINS`.

### 3. Run database migrations

Migrations run automatically on API container startup (`scripts/docker-entrypoint.sh`). First deploy triggers `alembic upgrade head`.

### 4. Seed Qdrant Cloud (one-off)

The seed job is **not** part of Terraform or Render startup. Run from your machine against the cloud cluster:

```bash
# From repo root — set Qdrant Cloud connection
export QDRANT_HOST="<host-from-endpoint-without-https>"
export QDRANT_PORT=6333
export QDRANT_API_KEY="<your-cluster-api-key>"
export GROQ_API_KEY="..."
export OPENROUTER_API_KEY="..."

uv sync --group dev
uv run python scripts/run_seed.py
```

Without seed data, `POST /interviews` returns **503** `RAG_NOT_READY`.

### 5. Smoke test

```bash
curl "$(terraform output -raw api_url)/health"
# Open frontend URL → register → login → complete interview
```

## What Terraform manages

- **`render_web_service.api`** — Docker build from repo `main` branch, health check on `/health`, env vars for DB, Qdrant, CORS, LLM keys.

## What Terraform does not manage

- Supabase project creation
- Qdrant cluster creation
- Vercel project / domain
- Qdrant seed ingestion
- GitHub Actions secrets (workflow template exists but is commented out)

## Remote state (optional)

[`versions.tf`](versions.tf) includes a commented HCP Terraform backend block. Uncomment and configure after creating an organization and workspace:

```bash
terraform login
terraform init
```

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| CORS errors in browser | `cors_origins` mismatch — update tfvars and re-apply |
| `503 RAG_NOT_READY` | Seed not run against Qdrant Cloud |
| `429 RATE_LIMIT_EXCEEDED` | Auth/global limits hit — defaults 5/min auth, 20/min global |
| Cold start timeout on free plan | Render free tier spins down — first request may be slow |

## Further reading

- Root [README](../README.md)
- [frontend/README.md](../frontend/README.md)
- [CHANGELOG.md](../CHANGELOG.md)
