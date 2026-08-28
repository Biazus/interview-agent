output "api_url" {
  description = "URL pública da API no Render"
  value       = render_web_service.api.url
}

output "supabase_project_ref" {
  description = "Project ref do Supabase (dashboard)"
  value       = var.supabase_project_ref
}

output "qdrant_cluster_id" {
  description = "ID do cluster Qdrant referenciado"
  value       = var.qdrant_cluster_id
}

output "qdrant_cluster_url" {
  description = "Endpoint do Qdrant Cloud"
  value       = var.qdrant_cluster_endpoint
}

output "vercel_hint" {
  description = "Frontend: conecte o repo em vercel.com e defina VITE_API_BASE_URL"
  value       = "VITE_API_BASE_URL=${render_web_service.api.url}"
}
