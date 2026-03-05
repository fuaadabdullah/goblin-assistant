#!/bin/bash
# Interactive secrets retrieval script

echo "🔐 Interactive Bitwarden Secrets Retrieval"
echo "=========================================="

cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Check if unlocked
if ! bw status | grep -q '"status":"unlocked"'; then
    echo "❌ Please unlock Bitwarden first:"
    echo "   bw unlock"
    exit 1
fi

echo "✅ Bitwarden unlocked"

# Sync
bw sync

# Get secrets
echo "🔑 Retrieving secrets..."

DATABASE_URL=$(bw list items --search "Database URL" | jq -r '.[0].login.password // empty')
JWT_SECRET_KEY=$(bw list items --search "JWT Secret" | jq -r '.[0].login.password // empty')
ANTHROPIC_API_KEY=$(bw list items --search "Anthropic API Key" | jq -r '.[0].login.password // empty')
OPENAI_API_KEY=$(bw list items --search "OpenAI API Key" | jq -r '.[0].login.password // empty')
SUPABASE_URL=$(bw list items --search "Supabase URL" | jq -r '.[0].login.password // empty')
SUPABASE_ANON_KEY=$(bw list items --search "Supabase Anon Key" | jq -r '.[0].login.password // empty')
SUPABASE_SERVICE_ROLE_KEY=$(bw list items --search "Supabase Service Role Key" | jq -r '.[0].login.password // empty')

# Update .env.production
echo "📝 Updating .env.production..."

cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)

[ -n "$DATABASE_URL" ] && sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" .env.production && echo "✅ DATABASE_URL updated"
[ -n "$JWT_SECRET_KEY" ] && sed -i.bak "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET_KEY|" .env.production && echo "✅ JWT_SECRET_KEY updated"
[ -n "$ANTHROPIC_API_KEY" ] && sed -i.bak "s|ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY|" .env.production && echo "✅ ANTHROPIC_API_KEY updated"
[ -n "$OPENAI_API_KEY" ] && sed -i.bak "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$OPENAI_API_KEY|" .env.production && echo "✅ OPENAI_API_KEY updated"
[ -n "$SUPABASE_URL" ] && sed -i.bak "s|SUPABASE_URL=.*|SUPABASE_URL=$SUPABASE_URL|" .env.production && echo "✅ SUPABASE_URL updated"
[ -n "$SUPABASE_ANON_KEY" ] && sed -i.bak "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY|" .env.production && echo "✅ SUPABASE_ANON_KEY updated"
[ -n "$SUPABASE_SERVICE_ROLE_KEY" ] && sed -i.bak "s|SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY|" .env.production && echo "✅ SUPABASE_SERVICE_ROLE_KEY updated"

rm -f .env.production.bak

echo ""
echo "🎉 Secrets retrieved and .env.production updated!"
echo "=================================================="
echo "Ready to deploy. Run:"
echo "  ./deploy-backend.sh fly"
