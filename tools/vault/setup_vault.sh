#!/bin/bash
# Goblin Assistant Vault Production Setup Script
# This script helps configure HashiCorp Vault for production use

set -e

echo "🔐 Goblin Assistant Vault Production Setup"
echo "=========================================="

# Check if vault CLI is installed
if ! command -v vault >/dev/null 2>&1; then
    echo "❌ Vault CLI not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install vault
    else
        # Linux installation
        wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com jammy main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
        sudo apt update && sudo apt install vault
    fi
fi

echo "✅ Vault CLI installed"

# Check if VAULT_ADDR is set
if [ -z "$VAULT_ADDR" ]; then
    echo ""
    echo "⚠️  VAULT_ADDR not set. Please configure:"
    echo "   export VAULT_ADDR='https://your-vault-server.com:8200'"
    echo ""
    echo "For local development, you can start Vault in dev mode:"
    echo "   vault server -dev"
    echo "   export VAULT_ADDR='http://127.0.0.1:8200'"
    echo "   export VAULT_TOKEN='dev-token'  # Copy from vault server output"
    exit 1
fi

# Check if VAULT_TOKEN is set
if [ -z "$VAULT_TOKEN" ]; then
    echo ""
    echo "⚠️  VAULT_TOKEN not set. Please configure:"
    echo "   export VAULT_TOKEN='your-vault-token'"
    echo ""
    echo "For local development, copy the token from vault server -dev output"
    exit 1
fi

echo "🔗 Testing Vault connection..."
if ! vault status >/dev/null 2>&1; then
    echo "❌ Cannot connect to Vault at $VAULT_ADDR"
    echo "   Please check your VAULT_ADDR and VAULT_TOKEN"
    exit 1
fi

echo "✅ Vault connection successful"

# Enable KV secrets engine if not already enabled
echo ""
echo "🔧 Configuring KV secrets engine..."
if ! vault secrets list | grep -q "^kv/"; then
    echo "   Enabling KV v2 secrets engine..."
    vault secrets enable -path=secret kv-v2
else
    echo "   KV secrets engine already enabled"
fi

# Create policy for goblin-assistant if it doesn't exist
echo ""
echo "📋 Setting up access policy..."
cat > /tmp/goblin-policy.hcl << EOF
path "secret/data/goblin-assistant*" {
  capabilities = ["read"]
}

path "secret/data/goblin-assistant/datadog*" {
  capabilities = ["read"]
}
EOF

vault policy write goblin-assistant /tmp/goblin-policy.hcl
rm /tmp/goblin-policy.hcl

echo "✅ Policy created"

# Test writing and reading a secret
echo ""
echo "🧪 Testing secret operations..."
echo "   Writing test secret..."
vault kv put secret/goblin-assistant/test test_key="test_value"

echo "   Reading test secret..."
if vault kv get secret/goblin-assistant/test | grep -q "test_key"; then
    echo "✅ Secret operations working"
    # Clean up test secret
    vault kv delete secret/goblin-assistant/test
else
    echo "❌ Secret operations failed"
    exit 1
fi

echo ""
echo "🎉 Vault production setup complete!"
echo ""
echo "Next steps:"
echo "1. Push your secrets: ./tools/vault/push_secrets.sh"
echo "2. Test secret retrieval: ./tools/vault/fetch_secrets.sh"
echo "3. Update your deployment with VAULT_ADDR and VAULT_TOKEN"
echo ""
echo "For production security:"
echo "- Use TLS certificates for Vault communication"
echo "- Rotate tokens regularly"
echo "- Enable audit logging"
echo "- Configure backup and recovery"
