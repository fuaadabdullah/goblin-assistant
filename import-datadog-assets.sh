#!/bin/bash
# Import Datadog Dashboard and Monitors for Goblin Assistant
# Run this after setting DATADOG_API_KEY and DATADOG_APP_KEY
# Or configure VAULT_ADDR and VAULT_TOKEN to load keys from Vault

set -e

echo "📊 Importing Datadog Dashboard and Monitors..."

# Function to load secrets from Vault
load_from_vault() {
    local vault_path="${1:-secret/goblin-assistant}"
    local key_name="$2"

    if command -v vault >/dev/null 2>&1 && [ -n "$VAULT_ADDR" ] && [ -n "$VAULT_TOKEN" ]; then
        echo "🔐 Loading $key_name from Vault..."
        vault kv get -field="$key_name" "$vault_path" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Try to load keys from Vault first, fallback to environment
DATADOG_API_KEY="${DATADOG_API_KEY:-$(load_from_vault secret/goblin-assistant/datadog DATADOG_API_KEY)}"
DATADOG_APP_KEY="${DATADOG_APP_KEY:-$(load_from_vault secret/goblin-assistant/datadog DATADOG_APP_KEY)}"

# Check if API keys are set
if [ -z "$DATADOG_API_KEY" ]; then
    echo "❌ DATADOG_API_KEY not set"
    echo "   Set environment variable or configure Vault with:"
    echo "   export DATADOG_API_KEY=your_key"
    echo "   Or: vault kv put secret/goblin-assistant/datadog DATADOG_API_KEY=your_key"
    exit 1
fi

if [ -z "$DATADOG_APP_KEY" ]; then
    echo "❌ DATADOG_APP_KEY not set"
    echo "   Set environment variable or configure Vault with:"
    echo "   export DATADOG_APP_KEY=your_key"
    echo "   Or: vault kv put secret/goblin-assistant/datadog DATADOG_APP_KEY=your_key"
    exit 1
fi

# Set Datadog site (change if not using US site)
DD_SITE="${DD_SITE:-datadoghq.com}"

echo "🌐 Using Datadog site: $DD_SITE"

# Import Dashboard
echo "📈 Importing dashboard..."
curl -X POST "https://api.${DD_SITE}/api/v1/dashboard" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @infra/datadog/dashboards/goblin-ops-dashboard.json

echo "✅ Dashboard imported!"

# Import Monitors
echo "🚨 Importing monitors..."

for monitor_file in infra/datadog/monitors/*.json; do
    echo "📋 Importing $(basename "$monitor_file")..."
    curl -X POST "https://api.${DD_SITE}/api/v1/monitor" \
      -H "Content-Type: application/json" \
      -H "DD-API-KEY: ${DATADOG_API_KEY}" \
      -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
      -d @"$monitor_file"
done

echo "✅ All monitors imported!"
echo ""
echo "🎯 Setup complete! Your monitoring is ready:"
echo "• Dashboard: Check https://app.${DD_SITE}/dashboard/lists"
echo "• Monitors: Check https://app.${DD_SITE}/monitors/manage"
echo ""
echo "🚀 Start your Goblin Assistant application to see metrics flowing in!"
