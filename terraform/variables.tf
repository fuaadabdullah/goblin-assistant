# Terraform Input Variables
# See terraform.tfvars.example for example values

variable "render_api_key" {
  description = "Render API key for authentication"
  type        = string
  sensitive   = true
}

variable "github_token" {
  description = "GitHub personal access token for state management and secret access"
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "GitHub repository owner (username or org)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "goblin-assistant"
}

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production"
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "goblin-assistant"
}

variable "region" {
  description = "Render region for deployment"
  type        = string
  default     = "oregon"
  validation {
    condition     = contains(["oregon", "ohio", "california"], var.region)
    error_message = "Region must be one of: oregon, ohio, california"
  }
}

# Service Configuration
variable "service_plan" {
  description = "Render service plan (starter, standard, pro, pro_plus)"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["starter", "standard", "pro", "pro_plus"], var.service_plan)
    error_message = "Service plan must be one of: starter, standard, pro, pro_plus"
  }
}

variable "num_instances" {
  description = "Number of instances for the backend service"
  type        = number
  default     = 2
  validation {
    condition     = var.num_instances >= 1 && var.num_instances <= 10
    error_message = "Number of instances must be between 1 and 10"
  }
}

# Docker Configuration
variable "docker_image_uri" {
  description = "Docker image URI for the backend service (if empty, uses GitHub Container Registry)"
  type        = string
  default     = ""
}

variable "docker_build_command" {
  description = "Docker build command"
  type        = string
  default     = "pip install --upgrade pip && pip install -r requirements.txt"
}

# Port Configuration
variable "port" {
  description = "Port for the backend service"
  type        = number
  default     = 8001
}

# Application Configuration
variable "app_environment" {
  description = "App environment setting (production, staging, development)"
  type        = string
  default     = "production"
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "info"
  validation {
    condition     = contains(["debug", "info", "warning", "error", "critical"], var.log_level)
    error_message = "Log level must be one of: debug, info, warning, error, critical"
  }
}

variable "debug_mode" {
  description = "Enable debug mode"
  type        = bool
  default     = false
}

# URLs and Origins
variable "frontend_url" {
  description = "Frontend URL (Vercel)"
  type        = string
  default     = "https://goblin-assistant.vercel.app"
}

variable "backend_url" {
  description = "Backend URL (Render)"
  type        = string
  default     = "https://goblin-assistant-backend.onrender.com"
}

variable "allowed_origins" {
  description = "Comma-separated list of allowed origins for CORS"
  type        = string
  default     = "https://goblin-assistant.vercel.app,https://goblin-assistant-backend.onrender.com"
}

# Rate Limiting
variable "rate_limit_enabled" {
  description = "Enable rate limiting"
  type        = bool
  default     = true
}

variable "rate_limit_requests" {
  description = "Rate limit: requests per window"
  type        = number
  default     = 100
}

variable "rate_limit_window" {
  description = "Rate limit: window in seconds"
  type        = number
  default     = 60
}

# Database Configuration (if using managed database)
variable "database_url" {
  description = "Database connection URL (PostgreSQL or Supabase)"
  type        = string
  sensitive   = true
  default     = ""
}

# Redis Configuration
variable "redis_url" {
  description = "Redis connection URL"
  type        = string
  sensitive   = true
  default     = ""
}

# Sentry Configuration
variable "sentry_dsn" {
  description = "Sentry DSN for error tracking"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sentry_traces_sample_rate" {
  description = "Sentry traces sample rate (0.0-1.0)"
  type        = number
  default     = 0.1
  validation {
    condition     = var.sentry_traces_sample_rate >= 0 && var.sentry_traces_sample_rate <= 1
    error_message = "Sentry traces sample rate must be between 0.0 and 1.0"
  }
}

variable "sentry_profiles_sample_rate" {
  description = "Sentry profiles sample rate (0.0-1.0)"
  type        = number
  default     = 0.01
  validation {
    condition     = var.sentry_profiles_sample_rate >= 0 && var.sentry_profiles_sample_rate <= 1
    error_message = "Sentry profiles sample rate must be between 0.0 and 1.0"
  }
}

# API Keys and Secrets (environment-specific)
variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_ai_api_key" {
  description = "Google AI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "jwt_secret_key" {
  description = "JWT secret key for authentication"
  type        = string
  sensitive   = true
  default     = ""
}

# Supabase Configuration
variable "supabase_url" {
  description = "Supabase project URL"
  type        = string
  sensitive   = true
  default     = ""
}

variable "supabase_service_role_key" {
  description = "Supabase service role key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "supabase_anon_key" {
  description = "Supabase anonymous key"
  type        = string
  sensitive   = true
  default     = ""
}

# AWS Configuration (optional)
variable "aws_access_key_id" {
  description = "AWS access key ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "aws_secret_access_key" {
  description = "AWS secret access key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Azure Configuration (optional)
variable "azure_api_key" {
  description = "Azure API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint"
  type        = string
  sensitive   = true
  default     = ""
}

# Release version
variable "release_version" {
  description = "Release version tag"
  type        = string
  default     = "goblin-assistant@1.0.0"
}

# Health check configuration
variable "health_check_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/health"
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  type        = number
  default     = 10
}

# GitHub Secrets Integration
variable "use_github_secrets" {
  description = "Whether to read secrets from GitHub repository"
  type        = bool
  default     = true
}

variable "github_secret_prefix" {
  description = "Prefix for GitHub secrets (e.g., 'RENDER_' for RENDER_DATABASE_URL)"
  type        = string
  default     = "RENDER_"
}
