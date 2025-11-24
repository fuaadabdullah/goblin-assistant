#!/bin/bash
# Complete Datadog Setup Script for Goblin Assistant
# Run this after manually installing the Datadog Agent

set -e

echo "🐕 Completing Datadog Agent Setup for Goblin Assistant..."

# Copy configuration
echo "📋 Copying configuration..."
sudo cp infra/datadog/datadog.yaml /opt/datadog-agent/etc/datadog.yaml
sudo chown dd-agent:dd-agent /opt/datadog-agent/etc/datadog.yaml

# Set API key in config (if environment variable is set)
if [ ! -z "$DATADOG_API_KEY" ]; then
    echo "🔑 Setting API key..."
    sudo sed -i.bak "s/api_key:.*/api_key: $DATADOG_API_KEY/" /opt/datadog-agent/etc/datadog.yaml
fi

# Start the agent
echo "🚀 Starting Datadog Agent..."
sudo datadog-agent start

# Check status
echo "📊 Checking agent status..."
sleep 5
sudo datadog-agent status | head -20

echo "✅ Datadog Agent setup complete!"
echo ""
echo "📈 Next steps:"
echo "1. Import dashboard: Upload infra/datadog/dashboards/goblin-ops-dashboard.json to Datadog"
echo "2. Import monitors: Upload the JSON files in infra/datadog/monitors/ to Datadog"
echo "3. Start your application with monitoring enabled"
echo "4. Check metrics in Datadog dashboard"
