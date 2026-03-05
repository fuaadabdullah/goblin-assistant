#!/bin/bash
# Script to retrieve secrets from Bitwarden and update .env.production

set -e

echo "🔐 Retrieving secrets from Bitwarden..."
echo "========================================"

# Check if Bitwarden is unlocked
if ! bw status | grep -q '"status":"unlocked"'; then
    echo "❌ Bitwarden vault is locked. Please unlock first:"
    echo "   bw unlock"
    exit 1
fi

# Sync vault
echo "📡 Syncing Bitwarden vault..."
bw sync

# Function to get secret by name
get_secret() {
    local name="$1"
    local result=$(bw list items --search "$name" | jq -r '.[0].login.password // empty')
    if [ -n "$result" ] && [ "$result" != "null" ]; then
        echo "$result"
    else
        echo ""
    fi
}

# Retrieve secrets
echo "🔑 Retrieving secrets..."

DATABASE_URL=$(get_secret "Database URL")
JWT_SECRET_KEY=$(get_secret "JWT Secret")
REDIS_URL=$(get_secret "Redis URL")
ANTHROPIC_API_KEY=$(get_secret "Anthropic API Key")
OPENAI_API_KEY=$(get_secret "OpenAI API Key")
SUPABASE_URL=$(get_secret "Supabase URL")
SUPABASE_ANON_KEY=$(get_secret "Supabase Anon Key")
SUPABASE_SERVICE_ROLE_KEY=$(get_secret "Supabase Service Role Key")
GOOGLE_CLIENT_ID=$(get_secret "Google Client ID")
GOOGLE_CLIENT_SECRET=$(get_secret "Google Client Secret")

# Update .env.production file
echo "📝 Updating .env.production..."

# Create backup
cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)

# Update each variable if found
if [ -n "$DATABASE_URL" ]; then
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" .env.production
    echo "✅ DATABASE_URL updated"
else
    echo "⚠️  DATABASE_URL not found in Bitwarden"
fi

if [ -n "$JWT_SECRET_KEY" ]; then
    sed -i.bak "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET_KEY|" .env.production
    echo "✅ JWT_SECRET_KEY updated"
else
    echo "⚠️  JWT_SECRET_KEY not found in Bitwarden"
fi

if [ -n "$REDIS_URL" ]; then
    sed -i.bak "s|REDIS_URL=.*|REDIS_URL=$REDIS_URL|" .env.production
    echo "✅ REDIS_URL updated"
else
    echo "⚠️  REDIS_URL not found in Bitwarden"
fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
    sed -i.bak "s|ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY|" .env.production
    echo "✅ ANTHROPIC_API_KEY updated"
else
    echo "⚠️  ANTHROPIC_API_KEY not found in Bitwarden"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    sed -i.bak "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$OPENAI_API_KEY|" .env.production
    echo "✅ OPENAI_API_KEY updated"
else
    echo "⚠️  OPENAI_API_KEY not found in Bitwarden"
fi

if [ -n "$SUPABASE_URL" ]; then
    sed -i.bak "s|SUPABASE_URL=.*|SUPABASE_URL=$SUPABASE_URL|" .env.production
    echo "✅ SUPABASE_URL updated"
else
    echo "⚠️  SUPABASE_URL not found in Bitwarden"
fi

if [ -n "$SUPABASE_ANON_KEY" ]; then
    sed -i.bak "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY|" .env.production
    echo "✅ SUPABASE_ANON_KEY updated"
else
    echo "⚠️  SUPABASE_ANON_KEY not found in Bitwarden"
fi

if [ -n "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    sed -i.bak "s|SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY|" .env.production
    echo "✅ SUPABASE_SERVICE_ROLE_KEY updated"
else
    echo "⚠️  SUPABASE_SERVICE_ROLE_KEY not found in Bitwarden"
fi

if [ -n "$GOOGLE_CLIENT_ID" ]; then
    sed -i.bak "s|GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID|" .env.production
    echo "✅ GOOGLE_CLIENT_ID updated"
else
    echo "⚠️  GOOGLE_CLIENT_ID not found in Bitwarden"
fi

if [ -n "$GOOGLE_CLIENT_SECRET" ]; then
    sed -i.bak "s|GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET|" .env.production
    echo "✅ GOOGLE_CLIENT_SECRET updated"
else
    echo "⚠️  GOOGLE_CLIENT_SECRET not found in Bitwarden"
fi

# Clean up backup files created by sed
rm -f .env.production.bak

echo ""
echo "🎉 Secrets retrieval complete!"
echo "=============================="
echo "✅ .env.production has been updated with secrets from Bitwarden"
echo "📋 Next steps:"
echo "   1. Review .env.production to ensure all values are correct"
echo "   2. Run deployment: ./deploy-backend.sh fly"
echo "   3. Update VITE_FASTAPI_URL in .env.production with the deployed backend URL"
echo "   4. Deploy frontend: ./deploy.sh vercel"
