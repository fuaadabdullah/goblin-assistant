# Redis Cache Configuration (Optional)
#
# This file contains configurations for Redis cache services.
# You have multiple options:
#
# Option 1: Render Managed Redis
#   - Render manages Redis for you
#   - Use render_redis resource below
#   - Simpler setup, less control
#
# Option 2: External Redis (already configured)
#   - Use REDIS_URL variable
#   - Set connection string in terraform.tfvars
#   - Currently might be using localhost (development)
#
# Option 3: Docker Redis (development)
#   - Using docker-compose.yml
#   - Not managed by Terraform
#

# Render Redis Database (optional - uncomment to use)
#
# resource "render_redis" "goblin_cache" {
#   name   = "${local.service_name}-cache"
#   region = var.region
#   plan   = "free"
#   
#   # Optional: configure eviction policy
#   max_memory_policy = "allkeys-lru"  # Evict least recently used keys when full
# }
#
# output "redis_url" {
#   description = "Redis connection string"
#   value       = render_redis.goblin_cache.internal_connection_string
#   sensitive   = true
# }

# Redis Connection Configuration
locals {
  redis_options = {
    render = {
      description = "Render managed Redis"
      requires    = "Uncomment render_redis resource"
      connection  = ""
    }
    docker_compose = {
      description = "Docker Compose Redis (development)"
      requires    = "docker-compose up redis"
      connection  = "redis://localhost:6379/0"
    }
    external = {
      description = "External/Managed Redis (AWS ElastiCache, etc.)"
      requires    = "redis_url variable"
      connection  = var.redis_url
    }
  }
}

# Informational output about Redis configuration
output "redis_info" {
  description = "Redis cache configuration information"
  value = {
    configured = var.redis_url != "" ? true : false
    connection_method = var.redis_url != "" ? "Configured via REDIS_URL" : "No Redis URL set"
    development_default = "redis://localhost:6379/0"
    notes = "For production, use Render managed Redis or external managed service (AWS ElastiCache, Azure Cache)"
  }
}
