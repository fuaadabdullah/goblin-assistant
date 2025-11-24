#!/bin/bash
# Install Datadog Agent on macOS (Local Dev)
# Run with: bash infra/datadog/install-macos.sh

set -e

echo "🐕 Installing Datadog Agent on macOS..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install Homebrew first: https://brew.sh/"
    exit 1
fi

# Install Datadog Agent
brew install datadog-agent

# Copy configuration
sudo mkdir -p /opt/datadog-agent/etc
sudo cp infra/datadog/datadog.yaml /opt/datadog-agent/etc/datadog.yaml

# Set environment variables (you should set these in your shell profile)
echo "⚠️  Please set the following environment variables:"
echo "export DATADOG_API_KEY=your-api-key-here"
echo "export DD_ENV=dev"
echo ""
echo "Add these to your ~/.zshrc or ~/.bash_profile"

# Start the agent
echo "🚀 Starting Datadog Agent..."
sudo datadog-agent start

echo "✅ Datadog Agent installed and started!"
echo "Check status: sudo datadog-agent status"
echo "View logs: sudo datadog-agent launch-gui"
