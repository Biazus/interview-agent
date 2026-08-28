resource "render_web_service" "api" {
  name              = "interview-agent-api"
  plan              = var.render_plan
  region            = "oregon"
  health_check_path = "/health"

  runtime_source = {
    docker = {
      auto_deploy     = true
      branch          = "main"
      repo_url        = var.github_repo_url
      dockerfile_path = "./Dockerfile"
    }
  }

  env_vars = {
    DATABASE_URL       = { value = local.database_url }
    QDRANT_HOST        = { value = local.qdrant_host }
    QDRANT_PORT        = { value = tostring(local.qdrant_port) }
    QDRANT_API_KEY     = { value = var.qdrant_cluster_api_key }
    CORS_ORIGINS       = { value = var.cors_origins }
    GROQ_API_KEY       = { value = var.groq_api_key }
    OPENROUTER_API_KEY = { value = var.openrouter_api_key }
    LOG_LEVEL          = { value = "INFO" }
  }
}
