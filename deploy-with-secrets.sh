#!/bin/bash
# Complete deployment script with Bitwarden secrets retrieval

set -e

echo "🚀 Goblin Assistant Production Deployment with Bitwarden Secrets"
echo "================================================================="

cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Check if Bitwarden is unlocked
echo "🔐 Checking Bitwarden status..."
if ! BW_SESSION_TOKEN="$BW_SESSION_TOKEN" bw status | grep -q '"status":"unlocked"'; then
    echo "❌ Bitwarden vault is locked."
    echo ""
    echo "Please unlock Bitwarden first:"
    echo "  bw unlock"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✅ Bitwarden is unlocked"

# Sync and retrieve secrets
echo "📡 Syncing Bitwarden vault..."
BW_SESSION_TOKEN="$BW_SESSION_TOKEN" bw sync

# Retrieve secrets using jq
echo "🔑 Retrieving secrets from Bitwarden..."

# Function to safely get secret
get_secret() {
    local name="$1"
    local result=$(BW_SESSION_TOKEN="$BW_SESSION_TOKEN" bw list items --search "$name" 2>/dev/null | jq -r '.[0].login.password // empty' 2>/dev/null || echo "")
    echo "$result"
}

# Get all secrets
DATABASE_URL=$(get_secret "Database URL")
JWT_SECRET_KEY=$(get_secret "JWT Secret")
REDIS_URL=$(get_secret "Redis URL")
ANTHROPIC_API_KEY=$(get_secret "Anthropic API Key")
OPENAI_API_KEY=$(get_secret "OpenAI API Key")
SUPABASE_URL=$(get_secret "Supabase URL")
SUPABASE_ANON_KEY=$(get_secret "Supabase Anon Key")
SUPABASE_SERVICE_ROLE_KEY=$(get_secret "Supabase Service Role Key")

echo "📝 Updating .env.production..."

# Create backup
cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)

# Update environment variables
[ -n "$DATABASE_URL" ] && sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" .env.production && echo "✅ DATABASE_URL updated"
[ -n "$JWT_SECRET_KEY" ] && sed -i.bak "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET_KEY|" .env.production && echo "✅ JWT_SECRET_KEY updated"
[ -n "$REDIS_URL" ] && sed -i.bak "s|REDIS_URL=.*|REDIS_URL=$REDIS_URL|" .env.production && echo "✅ REDIS_URL updated"
[ -n "$ANTHROPIC_API_KEY" ] && sed -i.bak "s|ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY|" .env.production && echo "✅ ANTHROPIC_API_KEY updated"
[ -n "$OPENAI_API_KEY" ] && sed -i.bak "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$OPENAI_API_KEY|" .env.production && echo "✅ OPENAI_API_KEY updated"
[ -n "$SUPABASE_URL" ] && sed -i.bak "s|SUPABASE_URL=.*|SUPABASE_URL=$SUPABASE_URL|" .env.production && echo "✅ SUPABASE_URL updated"
[ -n "$SUPABASE_ANON_KEY" ] && sed -i.bak "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY|" .env.production && echo "✅ SUPABASE_ANON_KEY updated"
[ -n "$SUPABASE_SERVICE_ROLE_KEY" ] && sed -i.bak "s|SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY|" .env.production && echo "✅ SUPABASE_SERVICE_ROLE_KEY updated"

# Clean up sed backup files
rm -f .env.production.bak

echo ""
echo "🎯 Starting Backend Deployment..."
echo "================================="

# Deploy backend
if [ -f "./deploy-backend.sh" ]; then
    echo "🚀 Deploying backend to Fly.io..."
    ./deploy-backend.sh fly
else
    echo "❌ deploy-backend.sh not found"
    exit 1
fi

echo ""
echo "🎯 Backend Deployment Complete!"
echo "==============================="
echo "📋 Next steps:"
echo "   1. Note the backend URL from Fly.io dashboard"
echo "   2. Update VITE_FASTAPI_URL in .env.production"
echo "   3. Run: ./deploy.sh vercel (for frontend deployment)"
echo ""
echo "✅ Deployment process completed successfully!"
