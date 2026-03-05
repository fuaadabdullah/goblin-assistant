#!/bin/bash
# Goblin Assistant - Test Bitwarden Vault Setup
# Verifies that secrets can be loaded from the vault
# Usage: ./test_vault.sh

set -e  # Exit on any error

echo "🧪 Testing Goblin Assistant Bitwarden Vault Setup"
echo "=================================================="

# Check if Bitwarden CLI is available
if ! command -v bw &> /dev/null; then
    echo "❌ Bitwarden CLI not found. Run setup_bitwarden.sh first"
    exit 1
fi

# Check if session is active
if [ -z "$BW_SESSION" ]; then
    echo "⚠️  BW_SESSION not set. Attempting to unlock..."
    export BW_SESSION=$(bw unlock --raw 2>/dev/null || echo "")
    if [ -z "$BW_SESSION" ]; then
        echo "❌ Could not unlock vault. Please run:"
        echo "export BW_SESSION=\$(bw unlock --raw)"
        exit 1
    fi
fi

echo "✅ Bitwarden session active"

# Test vault structure
echo ""
echo "📁 Checking vault structure..."

# Check if Infra Vault folder exists
VAULT_ITEMS=$(bw list items --folderid $(bw get folder "Infra Vault" | jq -r '.id') 2>/dev/null | jq length 2>/dev/null || echo "0")

if [ "$VAULT_ITEMS" -eq "0" ]; then
    echo "❌ Infra Vault folder not found or empty"
    echo "Run ./setup_bitwarden.sh to create the vault structure"
    exit 1
fi

echo "✅ Found $VAULT_ITEMS items in Infra Vault"

# Test loading secrets
echo ""
echo "🔐 Testing secret retrieval..."

TEST_SECRETS=(
    "goblin-dev-fastapi-secret"
    "goblin-dev-db-url"
    "goblin-dev-openai-key"
)

FAILED_SECRETS=()

for secret in "${TEST_SECRETS[@]}"; do
    echo -n "Testing $secret... "
    if bw get password "$secret" &>/dev/null; then
        echo "✅"
    else
        echo "❌"
        FAILED_SECRETS+=("$secret")
    fi
done

if [ ${#FAILED_SECRETS[@]} -ne 0 ]; then
    echo ""
    echo "❌ Some secrets could not be retrieved:"
    for secret in "${FAILED_SECRETS[@]}"; do
        echo "   - $secret"
    done
    echo ""
    echo "Make sure these items exist in your Bitwarden vault and have passwords set."
    exit 1
fi

echo ""
echo "🎉 Vault test successful!"
echo ""
echo "🚀 Ready to use:"
echo "   source scripts/load_env.sh    # Load development secrets"
echo "   ./deploy-vercel-bw.sh        # Deploy with vault secrets"
echo ""
echo "🧙‍♂️ Your goblin vault is operational!"
