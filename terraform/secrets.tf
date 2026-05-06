# Secrets Management Configuration
#
# This file handles sensitive environment variables and secrets management.
# Multiple options available:
#
# 1. GitHub Secrets (recommended for CI/CD)
#    - Store secrets in GitHub repository
#    - Reference via GITHUB_TOKEN in CI/CD
#    - Automatic sync to Terraform variables
#
# 2. Terraform Variables (terraform.tfvars)
#    - Store in .gitignore protected file
#    - Reference by variable name
#    - Manual management
#
# 3. Terraform Cloud (recommended for production)
#    - Encrypted secret storage
#    - Audit trail
#    - Team collaboration
#

# Local values for secrets structure
locals {
  secret_keys = {
    database_secrets = [
      "DATABASE_URL",
      "REDIS_URL",
    ]
    api_keys = [
      "OPENAI_API_KEY",
      "ANTHROPIC_API_KEY",
      "GOOGLE_AI_API_KEY",
    ]
    authentication = [
      "JWT_SECRET_KEY",
      "SUPABASE_SERVICE_ROLE_KEY",
      "SUPABASE_ANON_KEY",
    ]
    cloud_providers = [
      "AWS_ACCESS_KEY_ID",
      "AWS_SECRET_ACCESS_KEY",
      "AZURE_API_KEY",
      "AZURE_OPENAI_ENDPOINT",
    ]
    monitoring = [
      "SENTRY_DSN",
    ]
  }
}

# GitHub Secrets Data Source (optional)
# Enable this to read secrets from GitHub repository
# 
# Note: Requires github_token and GitHub provider
# See commented code at the end of this file

# Output information about secrets management
output "secrets_info" {
  description = "Secrets management configuration information"
  value = {
    management_options = [
      "1. GitHub Secrets (recommended for CI/CD workflows)",
      "2. Terraform Variables (terraform.tfvars)",
      "3. Terraform Cloud (recommended for production)",
    ]
    secret_categories = local.secret_keys
    setup_instructions = {
      github_secrets = "Store secrets in repository Settings → Secrets and variables → Actions"
      terraform_vars = "Create terraform.tfvars (add to .gitignore)"
      terraform_cloud = "Visit terraform.io for setup"
    }
    environment_variables_path = "terraform/variables.tf"
    example_tfvars_path = "terraform.tfvars.example"
  }
}

# Helper function to validate secrets (used in CI/CD)
# This can be called in GitHub Actions to verify all required secrets are set
locals {
  required_secrets_for_production = concat(
    local.secret_keys.database_secrets,
    local.secret_keys.api_keys,
    local.secret_keys.authentication,
    local.secret_keys.monitoring,
  )
  
  optional_secrets_for_production = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
  ]
}

# Output validation checklist
output "secrets_checklist" {
  description = "Checklist for secrets configuration"
  value = {
    required_for_production = local.required_secrets_for_production
    optional = local.optional_secrets_for_production
    setup_steps = [
      "1. Create terraform.tfvars from terraform.tfvars.example",
      "2. Fill in all required values",
      "3. Add terraform.tfvars to .gitignore",
      "4. For CI/CD: Add corresponding GitHub secrets with prefix (e.g., RENDER_DATABASE_URL)",
      "5. Verify in terraform plan output that secrets are being used"
    ]
  }
}

# Example of using GitHub Secrets in CI/CD
# Uncomment and adapt if using GitHub Actions with GitHub provider
#
# data "github_repository" "secrets" {
#   full_name = "${var.github_owner}/${var.github_repo}"
# }
#
# # Read secrets from GitHub (requires GitHub provider and token)
# # Then map them to Terraform variables
# locals {
#   github_secrets = {
#     for key in keys(local.secret_keys.database_secrets) :
#     key => try(
#       data.github_repository.secrets[key].secret_value,
#       ""
#     )
#   }
# }

# Output for CI/CD integration
output "cicd_secrets_setup" {
  description = "Setup instructions for CI/CD pipeline secrets"
  value = {
    github_actions = {
      location = "GitHub repository → Settings → Secrets and variables → Actions"
      variables_needed = [
        "RENDER_API_KEY - Get from Render dashboard",
        "For each environment variable in terraform/variables.tf, create corresponding GitHub secret",
        "Example: terraform variable 'database_url' → GitHub secret 'RENDER_DATABASE_URL'",
      ]
      workflow_reference = ".github/workflows/terraform-*.yml"
    }
    circleci = {
      location = "CircleCI project → Project Settings → Environment Variables"
      variables_needed = [
        "RENDER_API_KEY",
        "TERRAFORM_BACKEND_TOKEN (if using Terraform Cloud)",
      ]
    }
    best_practices = [
      "1. Never commit terraform.tfvars",
      "2. Rotate secrets regularly",
      "3. Use separate secrets for each environment (staging/production)",
      "4. Audit access to secrets in CI/CD",
      "5. Use encrypted backends for Terraform state",
    ]
  }
}
