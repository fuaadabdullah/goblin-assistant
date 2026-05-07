#!/bin/bash
# Goblin Assistant - Secrets Configuration Helper
# Helps configure production secrets in Bitwarden vault

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}🔐 GOBLIN ASSISTANT SECRETS CONFIGURATION${NC}"
    echo "=========================================="
    echo ""
}

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check vault status
check_vault() {
    print_info "Checking Bitwarden vault status..."

    if ! command -v bw &> /dev/null; then
        print_error "Bitwarden CLI not found. Install with: brew install bitwarden-cli"
        exit 1
    fi

    if ! bw status | grep -q "unlocked"; then
        print_error "Bitwarden vault is locked. Please unlock first:"
        echo "  bw unlock"
        echo "  export BW_SESSION='your_session_token'"
        exit 1
    fi

    print_status "Vault is unlocked and accessible"
}

# Check if secret exists
secret_exists() {
    local item_name=$1
    bw get password "$item_name" >/dev/null 2>&1
}

# Create or update secret
configure_secret() {
    local item_name=$1
    local description=$2
    local current_value=""

    if secret_exists "$item_name"; then
        current_value=$(bw get password "$item_name" 2>/dev/null || echo "")
        if [ -n "$current_value" ] && [ "$current_value" != "REDACTED" ]; then
            print_status "$item_name already configured"
            return 0
        fi
    fi

    print_warning "$item_name needs configuration"

    # Try to get value from environment or prompt
    local value=""
    local env_var=$(echo "$item_name" | sed 's/goblin-prod-//' | tr '-' '_' | tr '[:lower:]' '[:upper:]')

    if [ -n "${!env_var:-}" ]; then
        value="${!env_var}"
        print_info "Using value from $env_var environment variable"
    else
        print_info "Description: $description"
        echo -n "Enter value for $item_name (or press Enter to skip): "
        read -r value
        if [ -z "$value" ]; then
            print_warning "Skipping $item_name"
            return 1
        fi
    fi

    # Create or update the item
    if secret_exists "$item_name"; then
        # Update existing item
        local item_id=$(bw list items --search "$item_name" | jq -r '.[0].id' 2>/dev/null)
        if [ -n "$item_id" ] && [ "$item_id" != "null" ]; then
            bw edit item "$item_id" --login.password "$value" >/dev/null 2>&1
            print_status "Updated $item_name"
        fi
    else
        # Create new item
        bw create item <<EOF >/dev/null 2>&1
{
  "type": 1,
  "name": "$item_name",
  "login": {
    "password": "$value"
  }
}
EOF
        print_status "Created $item_name"
    fi
}

# Main configuration
main() {
    print_header

    check_vault

    echo ""
    print_info "Configuring production secrets..."
    echo ""

    # Database & Supabase
    configure_secret "goblin-prod-db-url" "PostgreSQL connection string (postgresql://user:pass@host:port/db)"
    configure_secret "goblin-prod-supabase-url" "Supabase project URL (https://xxxxx.supabase.co)"
    configure_secret "goblin-prod-supabase-service-role" "Supabase service role key"
    configure_secret "goblin-prod-supabase-anon" "Supabase anonymous key"

    # AI Providers
    configure_secret "goblin-prod-anthropic" "Anthropic API key"
    configure_secret "goblin-prod-openai" "OpenAI API key"

    # Monitoring & Error Tracking
    configure_secret "goblin-prod-sentry-dsn" "Sentry DSN for error tracking"
    configure_secret "goblin-prod-datadog-api" "Datadog API key"

    # Infrastructure
    configure_secret "goblin-prod-redis-url" "Redis connection URL"
    configure_secret "goblin-prod-fastapi-secret" "FastAPI secret key"
    configure_secret "goblin-prod-jwt" "JWT secret key"

    # Deployment Platforms
    configure_secret "goblin-prod-fly-token" "Fly.io API token"
    configure_secret "goblin-prod-cloudflare" "Cloudflare API token"
    configure_secret "goblin-prod-chromatic-token" "Chromatic project token"
    configure_secret "goblin-prod-vercel-token" "Vercel API token"
    configure_secret "goblin-prod-google-client-id" "Google OAuth client ID"

    echo ""
    print_info "Secrets configuration complete!"
    echo ""
    print_info "Next steps:"
    echo "1. Run: ./setup-production-env.sh --test"
    echo "2. If test passes: ./setup-production-env.sh (to generate runtime env)"
    echo "3. Deploy: ../../scripts/deploy/deploy-backend.sh --platform flyio --env staging"
}

# Run main function
main "$@"
