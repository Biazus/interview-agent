terraform {
  required_version = ">= 1.7.0"

  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.9"
    }
  }

  # Depois de criar org + workspace em https://app.terraform.io:
  # 1. Descomente o bloco abaixo
  # 2. Rode: terraform login && terraform init
  #
  # cloud {
  #   organization = "sua-org"
  #   workspaces {
  #     name = "interview-agent"
  #   }
  # }
}
