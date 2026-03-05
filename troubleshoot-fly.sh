#!/bin/bash
# Troubleshooting script for Fly.io deployment issues

echo "🔧 Fly.io Deployment Troubleshooting"
echo "===================================="

# Check current directory
echo "📁 Current directory: $(pwd)"
echo "📁 Contents:"
ls -la

# Check if Dockerfile exists and is valid
echo
echo "🐳 Checking Dockerfile..."
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile exists"
    echo "📄 Dockerfile contents:"
    head -20 Dockerfile
else
    echo "❌ Dockerfile not found"
fi

# Check requirements.txt
echo
echo "📦 Checking requirements.txt..."
if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt exists"
    echo "📄 First 10 lines:"
    head -10 requirements.txt
else
    echo "❌ requirements.txt not found"
fi

# Check start.sh
echo
echo "🚀 Checking start.sh..."
if [ -f "start.sh" ]; then
    echo "✅ start.sh exists"
    echo "📄 Start command:"
    grep "uvicorn" start.sh || echo "⚠️ uvicorn command not found"
else
    echo "❌ start.sh not found"
fi

# Check API package
echo
echo "📦 Checking API package..."
if [ -d "api" ]; then
    echo "✅ api directory exists"
    if [ -f "api/__init__.py" ]; then
        echo "✅ api/__init__.py exists"
    else
        echo "⚠️ api/__init__.py missing - creating..."
        touch api/__init__.py
    fi
    if [ -f "api/main.py" ]; then
        echo "✅ api/main.py exists"
        echo "📄 Import check:"
        python3 -c "import sys; sys.path.append('.'); import api.main; print('✅ Import successful')" 2>/dev/null || echo "❌ Import failed"
    else
        echo "❌ api/main.py not found"
    fi
else
    echo "❌ api directory not found"
fi

# Check fly.toml
echo
echo "🛫 Checking fly.toml..."
if [ -f "fly.toml" ]; then
    echo "✅ fly.toml exists"
    echo "📄 Build configuration:"
    grep -A 5 "\[build\]" fly.toml || echo "⚠️ [build] section not found"
    echo "📄 App name:"
    grep "app =" fly.toml || echo "⚠️ app name not found"
else
    echo "❌ fly.toml not found"
fi

# Test local build
echo
echo "🏗️ Testing local Docker build..."
if command -v docker &> /dev/null; then
    echo "🐳 Docker available - testing build..."
    docker build -t goblin-test . 2>&1 | head -20
    if [ $? -eq 0 ]; then
        echo "✅ Docker build successful"
    else
        echo "❌ Docker build failed"
    fi
else
    echo "⚠️ Docker not available for local testing"
fi

# Check for common issues
echo
echo "🔍 Common Issue Checks:"

# Check Python version compatibility
echo "🐍 Python version check:"
python3 --version

# Check for missing dependencies
echo "📦 Checking for missing imports in main.py:"
if [ -f "api/main.py" ]; then
    python3 -c "
import ast
import sys
sys.path.append('.')

try:
    with open('api/main.py', 'r') as f:
        tree = ast.parse(f.read())
    print('✅ main.py syntax is valid')
except SyntaxError as e:
    print(f'❌ Syntax error in main.py: {e}')
except Exception as e:
    print(f'⚠️ Could not parse main.py: {e}')
else:
    print('✅ main.py parsed successfully')
"

echo
echo "💡 Troubleshooting Tips:"
echo "1. Ensure all required files exist (Dockerfile, requirements.txt, api/main.py)"
echo "2. Check that PORT environment variable is set to 8001"
echo "3. Verify that the API package imports correctly"
echo "4. Make sure fly.toml has correct build configuration"
echo "5. Check Fly.io logs: fly logs"
echo "6. Test locally: docker build -t test . && docker run -p 8001:8001 test"

echo
echo "🚀 Ready to deploy? Run: fly deploy"
