# Terraform Outputs
# These values can be used by other Terraform modules or retrieved for CI/CD

output "service_id" {
  description = "Render service ID (set manually or via API)"
  value       = "Set in Render dashboard or via API deployment"
}

output "service_name" {
  description = "Render service name"
  value       = local.service_name
}

output "service_url" {
  description = "Render service public URL (set during deployment)"
  value       = var.backend_url
}

output "environment_variables" {
  description = "Environment variables applied to the service"
  value = {
    PORT                    = var.port
    ENVIRONMENT             = var.app_environment
    LOG_LEVEL               = var.log_level
    ALLOWED_ORIGINS         = var.allowed_origins
    RATE_LIMIT_ENABLED      = var.rate_limit_enabled
    RATE_LIMIT_REQUESTS     = var.rate_limit_requests
    RATE_LIMIT_WINDOW       = var.rate_limit_window
    NEXT_PUBLIC_API_BASE_URL = var.backend_url
    NEXT_PUBLIC_BACKEND_URL = var.backend_url
    NEXT_PUBLIC_FASTAPI_URL = var.backend_url
    NEXT_PUBLIC_FRONTEND_URL = var.frontend_url
  }
}

output "deployment_info" {
  description = "Deployment information"
  value = {
    region           = var.region
    plan             = var.service_plan
    num_instances    = var.num_instances
    docker_image     = local.docker_image
    environment      = var.environment
    deployment_time  = timestamp()
  }
}

output "terraform_commands" {
  description = "Useful Terraform commands for CI/CD"
  value = {
    plan  = "terraform plan -var-file terraform.tfvars"
    apply = "terraform apply -auto-approve -var-file terraform.tfvars"
    destroy = "terraform destroy -auto-approve -var-file terraform.tfvars"
  }
}

output "github_integration_notes" {
  description = "Notes for GitHub Actions integration"
  value = {
    required_secrets = [
      "RENDER_API_KEY",
      "GITHUB_TOKEN",
    ]
    workflow_example = "See .github/workflows/terraform-*.yml for complete examples"
    state_location   = "Configure in terraform/main.tf - options: Terraform Cloud, GitHub, Local"
  }
}
