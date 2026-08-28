terraform {
  required_version = ">= 1.7.0"

  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.9"
    }
  }

  cloud {
    organization = "biazus"      # substituir
    workspaces {
      name = "interview-agent"
   }
  }
}
