# PostgreSQL Database Configuration (Optional)
# 
# This file contains configurations for PostgreSQL database services.
# You have multiple options:
#
# Option 1: Render Managed PostgreSQL
#   - Render manages the database for you
#   - Use render_postgres resource below
#   - Simpler setup, less control
#
# Option 2: Supabase (recommended)
#   - Already using Supabase based on .env.example
#   - Managed PostgreSQL with additional features
#   - Set DATABASE_URL in terraform.tfvars
#   - No need to manage database resources here
#
# Option 3: External RDS/PostgreSQL
#   - Use DATABASE_URL variable
#   - Set connection string in terraform.tfvars
#   - No resources created here
#
# This file remains as an example for future use if you want to
# manage a dedicated database service.

# Render PostgreSQL Database (optional - uncomment to use)
# 
# resource "render_postgres" "goblin_db" {
#   name             = "${local.service_name}-db"
#   region           = var.region
#   database_name    = "goblin_assistant"
#   database_user    = "goblin_user"
#   version          = "15"
#   ipv4_cidr_block  = "10.0.0.0/16"
#   encrypted_password = random_password.db_password.result
# }
# 
# resource "random_password" "db_password" {
#   length  = 32
#   special = true
# }
#
# # Connection string
# output "database_url" {
#   description = "PostgreSQL connection string"
#   value       = "postgresql://${render_postgres.goblin_db.database_user}:${random_password.db_password.result}@${render_postgres.goblin_db.internal_connection_string}/${render_postgres.goblin_db.database_name}"
#   sensitive   = true
# }

# Database Configuration Notes
locals {
  database_options = {
    supabase = {
      description = "Managed PostgreSQL via Supabase (recommended)"
      requires    = "supabase_url, supabase_service_role_key, supabase_anon_key"
      connection  = var.database_url
    }
    render = {
      description = "Render managed PostgreSQL"
      requires    = "Uncomment render_postgres resource"
      connection  = ""
    }
    external = {
      description = "External PostgreSQL/RDS"
      requires    = "database_url variable"
      connection  = var.database_url
    }
  }
}

# Informational output about database configuration
output "database_info" {
  description = "Database configuration information"
  value = {
    configured    = var.database_url != "" ? true : false
    connection_method = var.database_url != "" ? "Configured via DATABASE_URL" : "No database URL set"
    provider      = "Supabase recommended (already in use based on .env.example)"
    notes         = "Update DATABASE_URL in terraform.tfvars with your Supabase connection string"
  }
}
