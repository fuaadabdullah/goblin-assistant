#!/bin/bash
# Goblin Assistant - Bitwarden Vault Setup Script
# Initializes Bitwarden CLI and creates the Infra Vault structure
# Usage: ./setup_bitwarden.sh

set -e  # Exit on any error

echo "🔮 Goblin Assistant - Bitwarden Infra Vault Setup"
echo "=================================================="

# Check if Bitwarden CLI is installed
if ! command -v bw &> /dev/null; then
    echo "❌ Bitwarden CLI not found. Installing..."
    npm install -g @bitwarden/cli
    echo "✅ Bitwarden CLI installed"
fi

echo "📋 Step 1: Login to Bitwarden"
echo "Please run the following commands manually:"
echo ""
echo "bw login YOUR_EMAIL@domain.com"
echo ""
echo "Then unlock your vault:"
echo "bw unlock --raw"
echo ""
echo "Copy the session token and export it:"
echo "export BW_SESSION='YOUR_SESSION_TOKEN_HERE'"
echo ""
read -p "Press Enter after you've completed the login steps above..."

# Verify session is working
if [ -z "$BW_SESSION" ]; then
    echo "❌ BW_SESSION not set. Please run:"
    echo "export BW_SESSION=\$(bw unlock --raw)"
    exit 1
fi

echo "✅ Bitwarden session verified"

# Create Infra Vault folder if it doesn't exist
echo "📁 Step 2: Creating Infra Vault folder..."
VAULT_FOLDER_ID=$(bw get folder Infra\ Vault 2>/dev/null | jq -r '.id' 2>/dev/null || echo "")

if [ -z "$VAULT_FOLDER_ID" ] || [ "$VAULT_FOLDER_ID" = "null" ]; then
    echo "Creating 'Infra Vault' folder..."
    bw get template folder | jq '.name="Infra Vault"' | bw encode | bw create folder
    VAULT_FOLDER_ID=$(bw get folder Infra\ Vault | jq -r '.id')
    echo "✅ Infra Vault folder created (ID: $VAULT_FOLDER_ID)"
else
    echo "✅ Infra Vault folder already exists (ID: $VAULT_FOLDER_ID)"
fi

echo ""
echo "🏗️ Step 3: Creating Secret Templates"
echo "===================================="

# Template for creating secrets
create_secret() {
    local name="$1"
    local notes="$2"

    echo "Creating: $name"
    bw get template item | \
    jq --arg name "$name" \
       --arg notes "$notes" \
       --arg folderId "$VAULT_FOLDER_ID" \
       '.type=1 | .name=$name | .notes=$notes | .folderId=$folderId | .login={} | .login.username="goblin-system"' | \
    bw encode | bw create item > /dev/null
}

# Development secrets
echo "🔧 Development Secrets:"
create_secret "goblin-dev-fastapi-secret" "FastAPI application secret key for development environment"
create_secret "goblin-dev-db-url" "Database connection URL for development"
create_secret "goblin-dev-jwt-secret" "JWT signing secret for development"
create_secret "goblin-dev-cloudflare-api" "Cloudflare API token for development"
create_secret "goblin-dev-openai-key" "OpenAI API key for development"
create_secret "goblin-dev-cloudinary-key" "Cloudinary API key for development"
create_secret "goblin-dev-groq-key" "Groq API key for development"
create_secret "goblin-dev-anthropic-key" "Anthropic API key for development"

# Production secrets
echo ""
echo "🚀 Production Secrets:"
create_secret "goblin-prod-fastapi-secret" "FastAPI application secret key for production environment"
create_secret "goblin-prod-db-url" "Database connection URL for production"
create_secret "goblin-prod-jwt-secret" "JWT signing secret for production"
create_secret "goblin-prod-cloudflare-api" "Cloudflare API token for production"
create_secret "goblin-prod-openai-key" "OpenAI API key for production"
create_secret "goblin-prod-cloudinary-key" "Cloudinary API key for production"
create_secret "goblin-prod-groq-key" "Groq API key for production"
create_secret "goblin-prod-anthropic-key" "Anthropic API key for production"

# SSH Key (optional)
echo ""
echo "🔑 SSH Key (Optional - High Risk):"
create_secret "goblin-ssh-private-key" "SSH private key for deployments (use with extreme caution)"

echo ""
echo "✅ Infra Vault structure created!"
echo ""
echo "📝 Next Steps:"
echo "=============="
echo ""
echo "1. Open Bitwarden web/app and navigate to 'Infra Vault' folder"
echo ""
echo "2. Edit each item to add the actual secret values:"
echo "   - goblin-dev-fastapi-secret: Generate a secure random string"
echo "   - goblin-dev-db-url: Your development database URL"
echo "   - goblin-dev-jwt-secret: Generate a secure JWT secret"
echo "   - And so on for all secrets..."
echo ""
echo "3. For production secrets, use different values than dev"
echo ""
echo "4. Test the setup:"
echo "   cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant"
echo "   source scripts/load_env.sh"
echo ""
echo "5. For deployments:"
echo "   ./deploy-vercel-bw.sh"
echo ""
echo "🧙‍♂️ Your goblin treasury is now established!"
echo "Remember: Rotate secrets regularly and never commit BW_SESSION"
