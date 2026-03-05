#!/bin/bash
# Goblin Assistant - CircleCI Secret Fetcher
# Pulls production secrets from Bitwarden vault for CI/CD deployment
# Usage: Called by CircleCI during deployment

set -e  # Exit on any error

echo "🔮 Goblin Assistant - Fetching Production Secrets from Bitwarden"
echo "================================================================"

# Verify BW_SESSION is set (should be set by CircleCI login step)
if [ -z "$BW_SESSION" ]; then
    echo "❌ BW_SESSION not set. CircleCI login step failed."
    exit 1
fi

echo "✅ Bitwarden session active"

# Sync vault to ensure latest secrets
echo "📦 Syncing Bitwarden vault..."
bw sync

# Fetch all production secrets
echo "🔐 Loading production secrets..."

export FASTAPI_SECRET=$(bw get password goblin-prod-fastapi-secret)
export DB_URL=$(bw get password goblin-prod-db-url)
export CF_TOKEN=$(bw get password goblin-prod-cloudflare)
export OPENAI_KEY=$(bw get password goblin-prod-openai)
export JWT_SECRET=$(bw get password goblin-prod-jwt)
export FLY_TOKEN=$(bw get password goblin-prod-fly-token)
export CHROMATIC_PROJECT_TOKEN=$(bw get password goblin-prod-chromatic-token)

# Optional: Load additional secrets as needed
# export GROQ_KEY=$(bw get password goblin-prod-groq)
# export ANTHROPIC_KEY=$(bw get password goblin-prod-anthropic)
# export CLOUDINARY_KEY=$(bw get password goblin-prod-cloudinary)

# Verify critical secrets are loaded
if [ -z "$FASTAPI_SECRET" ]; then
    echo "❌ Failed to load FASTAPI_SECRET"
    exit 1
fi

if [ -z "$DB_URL" ]; then
    echo "❌ Failed to load DB_URL"
    exit 1
fi

if [ -z "$FLY_TOKEN" ]; then
    echo "❌ Failed to load FLY_TOKEN"
    exit 1
fi

echo "✅ All critical secrets loaded successfully"
echo "🔒 Secrets ready for deployment"

# Export for CircleCI environment
echo "export FASTAPI_SECRET=\"$FASTAPI_SECRET\"" >> $BASH_ENV
echo "export DB_URL=\"$DB_URL\"" >> $BASH_ENV
echo "export CF_TOKEN=\"$CF_TOKEN\"" >> $BASH_ENV
echo "export OPENAI_KEY=\"$OPENAI_KEY\"" >> $BASH_ENV
echo "export JWT_SECRET=\"$JWT_SECRET\"" >> $BASH_ENV
echo "export FLY_TOKEN=\"$FLY_TOKEN\"" >> $BASH_ENV
echo "export CHROMATIC_PROJECT_TOKEN=\"$CHROMATIC_PROJECT_TOKEN\"" >> $BASH_ENV

echo "🧙‍♂️ Goblin secrets loaded into CircleCI environment"
