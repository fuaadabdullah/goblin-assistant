#!/bin/bash
# Deploy GoblinOS Assistant to Vercel with Bitwarden Secret Loading
# DEPRECATED: Use goblin-infra/projects/goblin-assistant/frontend/deploy-vercel.sh instead

set -e  # Exit on error

echo "⚠️  DEPRECATED: This script is deprecated."
echo "📍 Use: goblin-infra/projects/goblin-assistant/frontend/deploy-vercel.sh"
echo ""
echo "🔮 Deploying GoblinOS Assistant Frontend to Vercel (Bitwarden Vault)..."

# Navigate to project directory
cd "$(dirname "$0")"

# Check if Bitwarden CLI is installed
if ! command -v bw &> /dev/null; then
    echo "❌ Bitwarden CLI not found. Installing..."
    npm install -g @bitwarden/cli
fi

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Unlock Bitwarden vault
echo "🔐 Unlocking Bitwarden vault..."
export BW_SESSION=$(bw unlock --raw)

# Load production secrets
echo "📦 Loading production secrets from vault..."
export VERCEL_TOKEN=$(bw get password goblin-prod-vercel-token)
export GOOGLE_CLIENT_ID=$(bw get password goblin-prod-google-client-id)
export SUPABASE_URL=$(bw get password goblin-prod-supabase-url)
export SUPABASE_ANON_KEY=$(bw get password goblin-prod-supabase-anon-key)

echo "✅ Secrets loaded successfully"

# Authenticate with Vercel
echo "🔑 Authenticating with Vercel..."
vercel login --token "$VERCEL_TOKEN"

# Build the project
echo "📦 Building frontend..."
npm run build

# Set environment variables in Vercel
echo "🔧 Configuring Vercel environment..."
vercel env add VITE_API_URL production <<< "https://goblin-assistant.fly.dev"
vercel env add VITE_FASTAPI_URL production <<< "https://goblin-assistant.fly.dev"
vercel env add VITE_FRONTEND_URL production <<< "https://goblin-assistant.vercel.app"
vercel env add VITE_GOOGLE_CLIENT_ID production <<< "$GOOGLE_CLIENT_ID"
vercel env add VITE_APP_ENV production <<< "production"
vercel env add SUPABASE_URL production <<< "$SUPABASE_URL"
vercel env add SUPABASE_ANON_KEY production <<< "$SUPABASE_ANON_KEY"

# Deploy to Vercel
echo "🌐 Deploying to Vercel..."
vercel --prod

# Clean up session
unset BW_SESSION
unset VERCEL_TOKEN
unset GOOGLE_CLIENT_ID
unset SUPABASE_URL
unset SUPABASE_ANON_KEY

echo "✅ Frontend deployment complete!"
echo "🔗 URL: https://goblin-assistant.vercel.app"
echo ""
echo "🧹 Secrets cleaned from environment"
echo ""
echo "⚠️  NOTE: This script is deprecated. Use goblin-infra version for future deployments."
echo ""
echo "Next steps:"
echo "1. Deploy backend to Fly.io (see FLY_DEPLOYMENT.md or run ./deploy-fly.sh)"
echo "2. Verify environment variables in Vercel dashboard"
echo "3. Test the deployed application"
