# Render Backend Service Configuration
#
# Note: The Render Terraform provider has limited support for web services.
# This file documents the service configuration while actual deployment
# is managed via:
# 1. render.yaml for service definition
# 2. GitHub Actions workflow for API-based deployment
# 3. Render dashboard for service setup

# Service configuration (informational/reference)
locals {
  render_service_config = {
    name            = local.service_name
    runtime         = "docker"
    plan            = var.service_plan
    num_instances   = var.num_instances
    region          = var.region
    start_command   = "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
    health_path     = var.health_check_path
  }
}

# Output configuration for reference
output "render_deployment_config" {
  description = "Render service deployment configuration"
  value = {
    name           = local.render_service_config.name
    runtime        = local.render_service_config.runtime
    region         = local.render_service_config.region
    plan           = local.render_service_config.plan
    instances      = local.render_service_config.num_instances
    start_command  = local.render_service_config.start_command
    health_check   = local.render_service_config.health_path
  }
}

output "deployment_instructions" {
  description = "Instructions for deploying to Render"
  value = <<-EOT
    Render Deployment Instructions:
    
    1. Set up service in Render dashboard:
       - Visit: https://dashboard.render.com
       - New Web Service
       - Connect GitHub: ${var.github_owner}/${var.github_repo}
       - Branch: main
       - Build command: npm run build
       - Start command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
    
    2. Configure environment variables:
       - Add all values from terraform.tfvars via Render dashboard
       - Or use CI/CD to set them programmatically
    
    3. Enable auto-deploy:
       - GitHub integration should auto-deploy on push to main
       - Configure deployment trigger in Render settings
    
    4. API Deployment (via GitHub Actions):
       - GitHub Actions calls Render API to deploy
       - Uses RENDER_API_KEY for authentication
       - Triggered on main branch push automatically
  EOT
}

# GitHub integration via provider data source
output "github_integration_info" {
  description = "GitHub repository information for Render integration"
  value = {
    repository  = "${var.github_owner}/${var.github_repo}"
    branch      = "main"
    provider    = "github"
  }
}

output "environment_setup_checklist" {
  description = "Environment variables to configure"
  value = {
    required = {
      DATABASE_URL              = "PostgreSQL connection string"
      JWT_SECRET_KEY            = "JWT signing secret"
      SUPABASE_URL              = "Supabase project URL"
      SUPABASE_SERVICE_ROLE_KEY = "Supabase service role key"
      SUPABASE_ANON_KEY         = "Supabase anon key"
    }
    optional = {
      OPENAI_API_KEY      = "OpenAI API key (if using OpenAI)"
      ANTHROPIC_API_KEY   = "Anthropic API key (if using Claude)"
      GOOGLE_AI_API_KEY   = "Google AI API key (if using Gemini)"
      AWS_ACCESS_KEY_ID   = "AWS credentials (if using AWS services)"
      AZURE_API_KEY       = "Azure API key (if using Azure)"
      SENTRY_DSN          = "Sentry error tracking (if using Sentry)"
      REDIS_URL           = "Redis connection URL (if using cache)"
    }
  }
}
