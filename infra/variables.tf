variable "github_repo_url" {
  description = "URL HTTPS do repositório (ex.: https://github.com/seu-user/interview-agent)"
  type        = string
}

variable "cors_origins" {
  description = "Origens permitidas na API (URL do frontend na Vercel)"
  type        = string
  default     = "https://seu-app.vercel.app"
}

# --- Supabase (projeto existente) ---

variable "supabase_project_ref" {
  description = "Project ref (20 chars) — URL do dashboard ou host db.<ref>.supabase.co"
  type        = string
}

variable "database_url" {
  description = "Connection string do Postgres (Settings → Database). Aceita postgresql:// ou postgresql+asyncpg://"
  type        = string
  sensitive   = true
}

# --- Qdrant Cloud (cluster existente) ---

variable "qdrant_cluster_id" {
  description = "ID do cluster (UUID) — só referência/documentação"
  type        = string
}

variable "qdrant_cluster_endpoint" {
  description = "URL do cluster (ex.: https://xxx.sa-east-1-0.aws.cloud.qdrant.io)"
  type        = string
}

variable "qdrant_cluster_api_key" {
  description = "Database API key do cluster (eyJ... ou uuid|secret)"
  type        = string
  sensitive   = true
}

# --- Render ---

variable "render_plan" {
  description = "Plano do web service (free para demo; starter+ remove cold start)"
  type        = string
  default     = "free"
}

# --- Secrets da API (não commitar valores reais) ---

variable "groq_api_key" {
  type      = string
  sensitive = true
}

variable "openrouter_api_key" {
  type      = string
  sensitive = true
}
