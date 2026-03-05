#!/bin/bash

# Goblin Assistant - Bitwarden Environment Loader
# Loads secrets from Bitwarden vault into environment variables
# Usage: source load_env.sh

set -e  # Exit on any error

echo "🔮 Initializing Bitwarden session..."

# Unlock Bitwarden and export session token
export BW_SESSION=$(bw unlock --raw)

echo "✅ Bitwarden session established"

# Load development secrets
echo "📦 Loading development secrets..."

export FASTAPI_SECRET=$(bw get password goblin-dev-fastapi-secret)
export DB_URL=$(bw get password goblin-dev-db-url)
export CLOUDINARY_KEY=$(bw get password goblin-dev-cloudinary-key)
export OPENAI_KEY=$(bw get password goblin-dev-openai-key)

# Optional: Load additional secrets as needed
# export JWT_SECRET=$(bw get password goblin-dev-jwt-secret)
# export CLOUDFLARE_API=$(bw get password goblin-dev-cloudflare-api)

echo "🎭 Goblin environment loaded successfully!"
echo "Available secrets:"
echo "  FASTAPI_SECRET: ${FASTAPI_SECRET:0:10}..."
echo "  DB_URL: ${DB_URL:0:20}..."
echo "  CLOUDINARY_KEY: ${CLOUDINARY_KEY:0:10}..."
echo "  OPENAI_KEY: ${OPENAI_KEY:0:10}..."

echo "🧙‍♂️ Your terminal is now enchanted with goblin secrets."
