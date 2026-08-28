# Projeto Supabase já existente — referenciado por project_ref + connection string.
# project_ref: https://supabase.com/dashboard/project/<project_ref>
# database_url: Settings → Database → Connection string (modo URI)

locals {
  database_url = (
    startswith(var.database_url, "postgresql+asyncpg://")
    ? var.database_url
    : replace(var.database_url, "postgresql://", "postgresql+asyncpg://")
  )
}
