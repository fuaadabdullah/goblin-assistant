terraform {
  required_version = ">= 1.0"

  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.0"
    }
  }

  # Backend configuration for state management
  # Uncomment and configure based on your choice:
  
  # Option 1: GitHub (simple, free, no extra setup)
  # Store state in a private GitHub repository
  # Requires: GitHub token with repo scope
  # backend "http" {
  #   address = "https://api.github.com/repos/YOUR_USERNAME/YOUR_STATE_REPO/contents/terraform.tfstate"
  #   lock_address = "https://api.github.com/repos/YOUR_USERNAME/YOUR_STATE_REPO/contents/terraform.lock"
  #   username = "YOUR_GITHUB_USERNAME"
  #   password = "YOUR_GITHUB_TOKEN"
  # }
  
  # Option 2: Terraform Cloud (recommended, free tier available)
  # cloud {
  #   organization = "your-org-name"
  #   workspaces {
  #     name = "goblin-assistant"
  #   }
  # }
  
  # Option 3: Local state (development only)
  # backend "local" {
  #   path = "terraform.tfstate"
  # }
}

provider "render" {
  api_key = var.render_api_key
}

# Data source for the GitHub repository
data "github_repository" "main" {
  full_name = "${var.github_owner}/${var.github_repo}"
}

# Local variables for common tags/labels
locals {
  common_labels = {
    environment = var.environment
    project     = var.project_name
    managed_by  = "terraform"
    repo        = "${var.github_owner}/${var.github_repo}"
  }
  
  service_name = "${var.project_name}-backend"
  
  # Docker image reference
  docker_image = var.docker_image_uri != "" ? var.docker_image_uri : "ghcr.io/${var.github_owner}/${var.github_repo}:latest"
}
