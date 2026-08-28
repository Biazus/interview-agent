# Cluster já existente no Qdrant Cloud — só referenciamos via variáveis.
# (Alternativa: data "qdrant-cloud_accounts_cluster" + Management API key, ou terraform import.)

locals {
  qdrant_host = trimprefix(var.qdrant_cluster_endpoint, "https://")
  qdrant_port = 6333
}
