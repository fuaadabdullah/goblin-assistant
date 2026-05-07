#!/usr/bin/env bash
# Production Environment Setup Script
# Sets up production environment variables from secrets manager
# Usage: ./setup-production-env.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Parse command line arguments
TEST_MODE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --test)
      TEST_MODE=true
      shift
      ;;
    *)
      break
      ;;
  esac
done
if [ ! -f ".env.production" ]; then
    print_error "No .env.production file found. Run this script from the goblin-assistant directory."
    exit 1
fi

print_info "Setting up production environment variables..."

# Check if we're in CI (CircleCI) or local development
if [ -n "${CI:-}" ] || [ -n "${CIRCLECI:-}" ]; then
    print_info "Running in CI environment - using CircleCI contexts"

    # CircleCI should have already loaded secrets via fetch_secrets.sh
    # Verify critical secrets are available
    if [ -z "${FASTAPI_SECRET:-}" ]; then
        print_error "FASTAPI_SECRET not found in CI environment"
        exit 1
    fi

    if [ -z "${DB_URL:-}" ]; then
        print_error "DB_URL not found in CI environment"
        exit 1
    fi

    print_success "CI secrets verified"

else
    print_info "Running in local environment - checking Bitwarden"

    # Check if Bitwarden CLI is available
    if command -v bw &> /dev/null; then
        # Check if vault is unlocked
        if ! bw status | grep -q "unlocked"; then
            print_warning "Bitwarden vault is locked. Please unlock it first:"
            echo "  bw unlock"
            exit 1
        fi

        print_info "Fetching secrets from Bitwarden..."

        # Fetch secrets from Bitwarden (adjust item names as needed)
        export DATABASE_URL="$(bw get password "goblin-prod-db-url" 2>/dev/null || echo "postgresql://postgres:REDACTED@db.REDACTED.supabase.co:5432/postgres?sslmode=require")"
        export SUPABASE_URL="$(bw get password "goblin-prod-supabase-url" 2>/dev/null || echo "https://REDACTED.supabase.co")"
        export SUPABASE_SERVICE_ROLE_KEY="$(bw get password "goblin-prod-supabase-secret-key" 2>/dev/null || echo "REDACTED")"
        export SUPABASE_ANON_KEY="$(bw get password "goblin-prod-supabase-anon-key" 2>/dev/null || echo "REDACTED")"
        export ANTHROPIC_API_KEY="$(bw get password "goblin-prod-anthropic" 2>/dev/null || echo "REDACTED")"
        export OPENAI_API_KEY="$(bw get password "goblin-prod-openai" 2>/dev/null || echo "REDACTED")"
        export SENTRY_DSN="$(bw get password "goblin-prod-sentry-dsn" 2>/dev/null || echo "REDACTED")"
        export DD_API_KEY="$(bw get password "goblin-prod-datadog-api" 2>/dev/null || echo "REDACTED")"
        export REDIS_URL="$(bw get password "goblin-prod-redis-url" 2>/dev/null || echo "redis://localhost:6379/0")"
        export FASTAPI_SECRET_KEY="$(bw get password "goblin-prod-fastapi-secret" 2>/dev/null || echo "REDACTED")"
        export JWT_SECRET_KEY="$(bw get password "goblin-prod-jwt" 2>/dev/null || echo "REDACTED")"

        print_success "Secrets loaded from Bitwarden"
    else
        print_warning "Bitwarden CLI not found. Using placeholder values."
        print_info "Install Bitwarden CLI: brew install bitwarden-cli"
        print_info "Or set environment variables manually"
    fi
fi

# Create a temporary .env file with actual values for deployment
ENV_FILE=".env.production.runtime"
cp .env.production "$ENV_FILE"

# Replace REDACTED placeholders with actual values
if [ -n "${DATABASE_URL:-}" ]; then
    sed -i.bak "s|postgresql://postgres:REDACTED@db.REDACTED.supabase.co:5432/postgres?sslmode=require|$DATABASE_URL|g" "$ENV_FILE"
fi

if [ -n "${SUPABASE_URL:-}" ]; then
    sed -i.bak "s|https://REDACTED.supabase.co|$SUPABASE_URL|g" "$ENV_FILE"
fi

if [ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
    sed -i.bak "s|SUPABASE_SERVICE_ROLE_KEY=REDACTED|SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY|g" "$ENV_FILE"
fi

if [ -n "${SUPABASE_ANON_KEY:-}" ]; then
    sed -i.bak "s|SUPABASE_ANON_KEY=REDACTED|SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY|g" "$ENV_FILE"
fi

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    sed -i.bak "s|ANTHROPIC_API_KEY=REDACTED|ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY|g" "$ENV_FILE"
fi

if [ -n "${OPENAI_API_KEY:-}" ]; then
    sed -i.bak "s|OPENAI_API_KEY=REDACTED|OPENAI_API_KEY=$OPENAI_API_KEY|g" "$ENV_FILE"
fi

if [ -n "${SENTRY_DSN:-}" ]; then
    sed -i.bak "s|SENTRY_DSN=REDACTED|SENTRY_DSN=$SENTRY_DSN|g" "$ENV_FILE"
fi

if [ -n "${DD_API_KEY:-}" ]; then
    sed -i.bak "s|DD_API_KEY=REDACTED|DD_API_KEY=$DD_API_KEY|g" "$ENV_FILE"
fi

# Clean up backup files
rm -f "${ENV_FILE}.bak"

print_success "Production environment setup complete"
print_info "Runtime environment file created: $ENV_FILE"
print_warning "Remember: Never commit $ENV_FILE to version control"
print_info "Use this file for deployment, then delete it after use"

# Test mode: validate secrets are properly configured
if [ "$TEST_MODE" = true ]; then
    print_info "Running secrets validation test..."

    # Check if all required secrets are loaded (not REDACTED)
    MISSING_SECRETS=()

    check_secret() {
        local var_name=$1
        local secret_name=$2
        local value=${!var_name}

        if [ -z "$value" ] || [ "$value" = "REDACTED" ]; then
            MISSING_SECRETS+=("$secret_name")
        else
            print_success "✓ $secret_name configured"
        fi
    }

    # Test critical secrets
    check_secret "DATABASE_URL" "Database URL"
    check_secret "SUPABASE_URL" "Supabase URL"
    check_secret "SUPABASE_SERVICE_ROLE_KEY" "Supabase Service Role Key"
    check_secret "SUPABASE_ANON_KEY" "Supabase Anonymous Key"
    check_secret "SENTRY_DSN" "Sentry DSN"
    check_secret "DD_API_KEY" "Datadog API Key"
    check_secret "REDIS_URL" "Redis URL"

    if [ ${#MISSING_SECRETS[@]} -eq 0 ]; then
        print_success "🎉 All secrets are properly configured!"
        print_info "Ready for production deployment"
    else
        print_error "❌ Missing or placeholder secrets found:"
        for secret in "${MISSING_SECRETS[@]}"; do
            print_error "  - $secret"
        done
        print_warning "Please configure these secrets in Bitwarden before deploying"
        exit 1
    fi
fi
