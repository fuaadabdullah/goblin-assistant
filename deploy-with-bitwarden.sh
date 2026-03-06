#!/bin/bash

# Goblin Assistant - Secure Deployment Script
# Fetches secrets from Bitwarden and deploys both frontend and backend

set -e

echo "🔐 Goblin Assistant - Secure Deployment"
echo "======================================"

# Check Bitwarden CLI
if ! command -v bw &> /dev/null; then
    echo "❌ Bitwarden CLI not found. Install: brew install bitwarden-cli"
    exit 1
fi

if ! bw login --check &> /dev/null; then
    echo "❌ Not logged in to Bitwarden. Run: bw login"
    exit 1
fi

echo "✅ Bitwarden CLI ready"

# Unlock vault
if ! bw unlock --check &> /dev/null; then
    echo "🔑 Unlocking Bitwarden vault..."
    export BW_SESSION=$(bw unlock --raw)
fi

echo "🔓 Vault unlocked"

# Function to get secret from Bitwarden
get_secret() {
    local item_name="$1"
    local field="${2:-password}"  # Default to password field

    if [ "$field" = "password" ]; then
        bw get password "$item_name"
    else
        bw get item "$item_name" | jq -r ".fields[] | select(.name == \"$field\") | .value"
    fi
}

echo "🔑 Fetching secrets from Bitwarden..."

# Supabase secrets
export NEXT_PUBLIC_SUPABASE_URL=$(get_secret "Supabase URL")
export NEXT_PUBLIC_SUPABASE_ANON_KEY=$(get_secret "Supabase Anon Key")
export SUPABASE_SERVICE_ROLE_KEY=$(get_secret "Supabase Service Role Key")
export DATABASE_URL=$(get_secret "Database URL")

# Google OAuth
export GOOGLE_CLIENT_ID=$(get_secret "Google Client ID")
export GOOGLE_CLIENT_SECRET=$(get_secret "Google Client Secret")

# JWT Secrets
export JWT_SECRET_KEY=$(get_secret "JWT Secret Key")
export JWT_STANDBY_KEY=$(get_secret "JWT Standby Key")
export JWT_CURRENT_KEY=$(get_secret "JWT Current Key")

# AI Provider Keys
export OPENAI_API_KEY=$(get_secret "OpenAI API Key")
export ANTHROPIC_API_KEY=$(get_secret "Anthropic API Key")
export DEEPSEEK_API_KEY=$(get_secret "DeepSeek API Key")
export GOOGLE_GEMINI_API_KEY=$(get_secret "Google Gemini API Key")
export XAI_GROK_API_KEY=$(get_secret "xAI Grok API Key")
export SILICONFLOW_API_KEY=$(get_secret "SiliconFlow API Key")
export MOONSHOT_API_KEY=$(get_secret "Moonshot API Key")
export ELEVENLABS_API_KEY=$(get_secret "ElevenLabs API Key")

# Infrastructure
export SENTRY_ADMIN_TOKEN=$(get_secret "Sentry Admin Token")
export KAMATERA_HOST=$(get_secret "Kamatera Host")
export KAMATERA_LLM_URL=$(get_secret "Kamatera LLM URL")
export KAMATERA_LLM_API_KEY=$(get_secret "Kamatera LLM API Key")

# Cloudflare Turnstile
export TURNSTILE_SITE_KEY=$(get_secret "Turnstile Site Key")
export TURNSTILE_SECRET_KEY=$(get_secret "Turnstile Secret Key")

echo "✅ All secrets loaded"

# Verify secrets are loaded
if [ -z "$NEXT_PUBLIC_SUPABASE_URL" ]; then
    echo "❌ Failed to load Supabase URL"
    exit 1
fi

echo "🚀 Starting deployment..."

# Deploy frontend to Vercel
echo "📦 Deploying frontend to Vercel..."
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Create temporary .env.local for Vercel
cat > .env.local << ENV_EOF
NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET
OPENAI_API_KEY=$OPENAI_API_KEY
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY
GOOGLE_GEMINI_API_KEY=$GOOGLE_GEMINI_API_KEY
XAI_GROK_API_KEY=$XAI_GROK_API_KEY
SILICONFLOW_API_KEY=$SILICONFLOW_API_KEY
MOONSHOT_API_KEY=$MOONSHOT_API_KEY
ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY
SENTRY_ADMIN_TOKEN=$SENTRY_ADMIN_TOKEN
KAMATERA_HOST=$KAMATERA_HOST
KAMATERA_LLM_URL=$KAMATERA_LLM_URL
KAMATERA_LLM_API_KEY=$KAMATERA_LLM_API_KEY
VITE_TURNSTILE_SITE_KEY=$TURNSTILE_SITE_KEY
ENV_EOF

# Deploy to Vercel
vercel --prod --yes

# Clean up temporary file
rm .env.local

echo "✅ Frontend deployed"

# Deploy backend to Fly.io
echo "🛠️  Deploying backend to Fly.io..."

# Create temporary .env for Fly.io in backend directory
cat > backend/.env << ENV_EOF
SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY
DATABASE_URL=$DATABASE_URL
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_STANDBY_KEY=$JWT_STANDBY_KEY
JWT_CURRENT_KEY=$JWT_CURRENT_KEY
OPENAI_API_KEY=$OPENAI_API_KEY
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY
GOOGLE_GEMINI_API_KEY=$GOOGLE_GEMINI_API_KEY
XAI_GROK_API_KEY=$XAI_GROK_API_KEY
SILICONFLOW_API_KEY=$SILICONFLOW_API_KEY
MOONSHOT_API_KEY=$MOONSHOT_API_KEY
ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY
SENTRY_ADMIN_TOKEN=$SENTRY_ADMIN_TOKEN
KAMATERA_HOST=$KAMATERA_HOST
KAMATERA_LLM_URL=$KAMATERA_LLM_URL
KAMATERA_LLM_API_KEY=$KAMATERA_LLM_API_KEY
TURNSTILE_SECRET_KEY=$TURNSTILE_SECRET_KEY
ENV_EOF

# Deploy to Fly.io from root directory
fly deploy --yes

# Clean up temporary file
rm backend/.env

echo "✅ Backend deployed"

# Lock vault
unset BW_SESSION

echo ""
echo "🎉 Deployment complete!"
echo "🔒 Vault locked for security"
echo ""
echo "📊 Deployment Summary:"
echo "   Frontend: https://goblin-assistant.vercel.app"
echo "   Backend API: https://goblin-assistant-backend.onrender.com"
echo "   Admin Panel: https://goblin-assistant.vercel.app"
echo ""
echo "🔄 Next Steps:"
echo "   1. Test the deployed application"
echo "   2. Monitor logs for any issues"
echo "   3. Remove .env.backup files if everything works"
echo ""
