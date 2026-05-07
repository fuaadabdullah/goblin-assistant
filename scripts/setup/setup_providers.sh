#!/bin/bash
# Setup script for SiliconeFlow and LlamaCPP configuration

echo "======================================================================="
echo "🔧 Goblin Assistant - Provider Setup Helper"
echo "======================================================================="
echo ""

# Check for .env.local
if [ ! -f ".env.local" ]; then
    echo "❌ .env.local not found!"
    echo "Creating from .env.example..."
    cp .env.example .env.local
fi

echo "📝 Current Configuration:"
echo ""

# Show current SiliconeFlow key (masked)
if grep -q "SILICONEFLOW_API_KEY=" .env.local; then
    current_key=$(grep "SILICONEFLOW_API_KEY=" .env.local | cut -d= -f2)
    if [ -z "$current_key" ] || [ "$current_key" = "your_siliconeflow_key_here" ]; then
        echo "❌ SiliconeFlow: Not configured (placeholder)"
    else
        echo "✅ SiliconeFlow: ${current_key:0:10}...${current_key: -4}"
    fi
else
    echo "❌ SiliconeFlow: Not in .env.local"
fi

# Show LlamaCPP endpoint
if grep -q "LLAMACPP_GCP_URL=" .env.local; then
    llamacpp_url=$(grep "LLAMACPP_GCP_URL=" .env.local | cut -d= -f2)
    echo "📍 LlamaCPP URL: $llamacpp_url"
else
    echo "❌ LlamaCPP URL: Not configured"
fi

echo ""
echo "======================================================================="
echo "🔑 SiliconeFlow API Key Setup"
echo "======================================================================="
echo ""
echo "If you have your SiliconeFlow API key, you can:"
echo ""
echo "Option 1: Edit .env.local directly"
echo "  nano .env.local"
echo "  # Add or update: SILICONEFLOW_API_KEY=your_actual_key_here"
echo ""
echo "Option 2: Use this command (replace YOUR_KEY with your actual key):"
echo "  ./setup_siliconeflow.sh YOUR_KEY"
echo ""
echo "Get your key from: https://cloud.siliconflow.cn/account/ak"
echo ""

echo "======================================================================="
echo "🖥️  LlamaCPP Server Diagnostics"
echo "======================================================================="
echo ""
echo "Testing LlamaCPP endpoint connectivity..."
echo ""

# Test LlamaCPP connectivity
llamacpp_url=$(grep "LLAMACPP_GCP_URL=" .env.local 2>/dev/null | cut -d= -f2 | tr -d '\r')
if [ -n "$llamacpp_url" ]; then
    host=$(echo $llamacpp_url | sed 's|http://||' | sed 's|https://||' | cut -d: -f1)
    port=$(echo $llamacpp_url | sed 's|http://||' | sed 's|https://||' | cut -d: -f2 | cut -d/ -f1)
    
    echo "Testing: $host:$port"
    
    # Try to connect
    if command -v nc &> /dev/null; then
        if timeout 3 nc -zv $host $port 2>&1 | grep -q "succeeded"; then
            echo "✅ Port is open and reachable"
        else
            echo "❌ Cannot connect to $host:$port"
            echo ""
            echo "Possible issues:"
            echo "  • Server is down"
            echo "  • Firewall blocking port $port"
            echo "  • Wrong IP/port configuration"
        fi
    else
        echo "⚠️  'nc' command not available, skipping connectivity test"
    fi
fi

echo ""
echo "======================================================================="
echo "✨ Next Steps"
echo "======================================================================="
echo ""
echo "1. Add your SiliconeFlow API key to .env.local"
echo "   SILICONEFLOW_API_KEY=sk-xxxxxxxxxxxxxxxxxx"
echo ""
echo "2. For LlamaCPP, try these alternatives:"
echo "   a) Use Ollama GCP instead (it's working!)"
echo "   b) Check if LlamaCPP server is running on GCP"
echo "   c) Use local LlamaCPP: http://localhost:8080"
echo ""
echo "3. Test the configuration:"
echo "   python3 test_providers_quick.py"
echo ""
echo "4. Run full benchmarks:"
echo "   python3 benchmark_providers.py"
echo ""
