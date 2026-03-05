#!/bin/bash

# Configure Kamatera Providers for Goblin Assistant Backend
# This script sets up the correct endpoints for Ollama and llama.cpp on Kamatera

set -e

echo "🚀 Configuring Kamatera Providers..."

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl is not installed. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Configuration
APP_NAME="goblin-backend"

# Check if app exists
if ! flyctl apps list | grep -q "$APP_NAME"; then
    echo "❌ App $APP_NAME not found. Please create it first:"
    echo "   flyctl apps create $APP_NAME"
    exit 1
fi

echo "📋 Configuring Kamatera endpoints for app: $APP_NAME"

# Kamatera Server Configuration
echo "📡 Kamatera Server Configuration"
echo "=================================="

# Get current Kamatera endpoints
echo "Current Kamatera endpoints in providers.toml:"
echo "  Ollama (Kamatera): http://45.61.60.3:8002"
echo "  llama.cpp (Kamatera): http://45.61.60.3:8002"
echo ""

# Ask user for Kamatera server details
read -p "❓ Do you have Kamatera servers configured? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 Please provide your Kamatera server details:"
    echo ""
    
    # Ollama on Kamatera
    read -p "🔗 Ollama Kamatera URL (e.g., http://your-ip:8002): " OLLAMA_KAMATERA_URL
    if [ -n "$OLLAMA_KAMATERA_URL" ]; then
        echo "✅ Ollama Kamatera URL: $OLLAMA_KAMATERA_URL"
    else
        echo "⚠️  Using default Ollama Kamatera URL: http://45.61.60.3:8002"
        OLLAMA_KAMATERA_URL="http://45.61.60.3:8002"
    fi
    
    # llama.cpp on Kamatera
    read -p "🔗 llama.cpp Kamatera URL (e.g., http://your-ip:8000): " LLAMACPP_KAMATERA_URL
    if [ -n "$LLAMACPP_KAMATERA_URL" ]; then
        echo "✅ llama.cpp Kamatera URL: $LLAMACPP_KAMATERA_URL"
    else
        echo "⚠️  Using default llama.cpp Kamatera URL: http://45.61.60.3:8000"
        LLAMACPP_KAMATERA_URL="http://45.61.60.3:8000"
    fi
    
    # Test connectivity
    echo ""
    echo "🔍 Testing connectivity to Kamatera servers..."
    
    # Test Ollama
    if curl -s --connect-timeout 5 "$OLLAMA_KAMATERA_URL" > /dev/null; then
        echo "✅ Ollama Kamatera server is reachable"
    else
        echo "❌ Ollama Kamatera server is not reachable at $OLLAMA_KAMATERA_URL"
        echo "   Please check your server configuration and firewall settings"
    fi
    
    # Test llama.cpp
    if curl -s --connect-timeout 5 "$LLAMACPP_KAMATERA_URL" > /dev/null; then
        echo "✅ llama.cpp Kamatera server is reachable"
    else
        echo "❌ llama.cpp Kamatera server is not reachable at $LLAMACPP_KAMATERA_URL"
        echo "   Please check your server configuration and firewall settings"
    fi
    
    echo ""
    echo "🎯 Kamatera Provider Configuration Summary:"
    echo "=========================================="
    echo "  Ollama (Kamatera): $OLLAMA_KAMATERA_URL"
    echo "  llama.cpp (Kamatera): $LLAMACPP_KAMATERA_URL"
    echo ""
    
    # Update providers.toml with new endpoints
    echo "📝 Updating providers.toml configuration..."
    
    # Backup original file
    cp config/providers.toml config/providers.toml.backup
    
    # Update Ollama Kamatera endpoint
    sed -i.bak "s|endpoint = \"http://45.61.60.3:8002\"|endpoint = \"$OLLAMA_KAMATERA_URL\"|" config/providers.toml
    
    # Update llama.cpp Kamatera endpoint
    sed -i.bak "s|endpoint = \"http://45.61.60.3:8002\"|endpoint = \"$LLAMACPP_KAMATERA_URL\"|" config/providers.toml
    
    # Clean up backup files
    rm -f config/providers.toml.bak
    
    echo "✅ providers.toml updated successfully"
    
    # Set environment variables for Kamatera services
    echo ""
    echo "🔧 Setting Kamatera environment variables..."
    
    flyctl secrets set \
        KAMATERA_SERVER1_URL="$OLLAMA_KAMATERA_URL" \
        KAMATERA_SERVER2_URL="$LLAMACPP_KAMATERA_URL"
    
    echo "✅ Kamatera environment variables set"
    
else
    echo "⚠️  Skipping Kamatera configuration"
    echo "   Kamatera providers will remain disabled"
fi

echo ""
echo "🎯 Kamatera Configuration Complete!"
echo "=================================="
echo ""
echo "📋 Next Steps:"
echo "1. Verify your Kamatera servers are running:"
echo "   - Ollama on Kamatera: $OLLAMA_KAMATERA_URL"
echo "   - llama.cpp on Kamatera: $LLAMACPP_KAMATERA_URL"
echo ""
echo "2. Deploy the updated configuration:"
echo "   flyctl deploy -a $APP_NAME"
echo ""
echo "3. Test Kamatera providers:"
echo "   curl https://$APP_NAME.fly.dev/health"
echo ""
echo "🆘 Troubleshooting:"
echo "- Ensure Kamatera servers allow connections from Fly.io"
echo "- Check firewall settings on Kamatera servers"
echo "- Verify Ollama and llama.cpp are running on Kamatera"
echo "- Check logs: flyctl logs -a $APP_NAME"
