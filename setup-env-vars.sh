#!/bin/bash
# Script to set production environment variables in Fly.io
# Run this after getting your secrets from Bitwarden or other sources

set -e

echo "🔧 Setting Production Environment Variables for Goblin Assistant"
echo "=================================================================="

cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Check if Fly CLI is available
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Please install it first."
    exit 1
fi

echo "📋 Required Environment Variables:"
echo "=================================="
echo ""
echo "🔑 CRITICAL (Required for app to start):"
echo "  - DATABASE_URL: PostgreSQL connection string"
echo "  - JWT_SECRET_KEY: Random secure string for authentication"
echo "  - SUPABASE_URL: Your Supabase project URL"
echo "  - SUPABASE_ANON_KEY: Supabase anonymous key"
echo "  - SUPABASE_SERVICE_ROLE_KEY: Supabase service role key"
echo ""
echo "🤖 AI PROVIDERS (At least one required):"
echo "  - ANTHROPIC_API_KEY: Claude API key"
echo "  - OPENAI_API_KEY: OpenAI API key"
echo "  - GOOGLE_AI_API_KEY: Google Gemini API key"
echo ""
echo "⚡ OPTIONAL (But recommended):"
echo "  - REDIS_URL: Redis connection string for sessions"
echo "  - FRONTEND_URL: Your production frontend URL"
echo "  - ALLOWED_ORIGINS: CORS allowed origins"
echo ""

# Function to set environment variable
set_env_var() {
    local key="$1"
    local value="$2"
    if [ -n "$value" ] && [ "$value" != "your-"* ] && [ "$value" != "https://your-"* ]; then
        echo "Setting $key..."
        fly secrets set "$key=$value"
    else
        echo "⚠️  Skipping $key (empty or placeholder value)"
    fi
}

echo "🔄 Setting environment variables from .env.production..."
echo "======================================================="

# Read .env.production and set variables
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ $key =~ ^[[:space:]]*# ]] && continue
    [[ -z "$key" ]] && continue

    # Remove quotes if present
    value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/")

    # Skip VITE_ variables (these are for frontend)
    if [[ $key == VITE_* ]]; then
        continue
    fi

    set_env_var "$key" "$value"
done < .env.production

echo ""
echo "✅ Environment variables setup complete!"
echo "========================================="
echo ""
echo "📋 Next Steps:"
echo "=============="
echo "1. Check your app status: fly apps list"
echo "2. View app logs: fly logs"
echo "3. Test health endpoint: curl https://goblin-backend.fly.dev/health"
echo "4. Update frontend VITE_FASTAPI_URL with: https://goblin-backend.fly.dev"
echo "5. Deploy frontend: ./deploy.sh vercel"
echo ""
echo "🔧 If you need to update any variables:"
echo "   fly secrets set KEY=VALUE"
echo ""
echo "📊 Monitor your deployment:"
echo "   fly dashboard"
echo "   fly logs -a goblin-backend"
