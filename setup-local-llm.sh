#!/bin/bash

# Goblin Assistant Local LLM Setup Script
# This script helps set up Ollama, LM Studio, and llama.cpp for local AI model inference

set -e

echo "🤖 Goblin Assistant Local LLM Setup"
echo "===================================="

# Check if Ollama is available
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is installed"
    OLLAMA_INSTALLED=true
else
    echo "❌ Ollama not found in PATH"
    OLLAMA_INSTALLED=false
fi

# Check for archived Ollama on USB
ARCHIVED_OLLAMA_PATH="/Volumes/Fuaad 1/Storage_Hierarchy/Development/Dependencies/ollama_old"
if [ -d "$ARCHIVED_OLLAMA_PATH" ]; then
    echo "📁 Found archived Ollama at: $ARCHIVED_OLLAMA_PATH"
    echo "   Models available:"
    ls -la "$ARCHIVED_OLLAMA_PATH/models/blobs/" | wc -l | xargs echo "   - Models found:"
else
    echo "❌ Archived Ollama not found on USB"
fi

# Setup Ollama
if [ "$OLLAMA_INSTALLED" = true ]; then
    echo ""
    echo "🔄 Setting up Ollama..."

    # Start Ollama service
    echo "Starting Ollama service..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2

    # Check if service is running
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "✅ Ollama service is running on http://localhost:11434"

        # Pull recommended models
        echo "📥 Pulling recommended models..."
        ollama pull qwen2.5:3b || echo "⚠️  Failed to pull qwen2.5:3b"
        ollama pull llama2:7b || echo "⚠️  Failed to pull llama2:7b"

        echo "📋 Available models:"
        ollama list
    else
        echo "❌ Failed to start Ollama service"
    fi
fi

# Setup llama.cpp
echo ""
echo "🔄 Setting up llama.cpp..."

# Check if llama.cpp server is available
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ llama.cpp server is running on http://localhost:8080"
else
    echo "❌ llama.cpp server not found on http://localhost:8080"
    echo ""
    echo "To set up llama.cpp:"
    echo "1. Clone llama.cpp: git clone https://github.com/ggerganov/llama.cpp"
    echo "2. Build: cd llama.cpp && make"
    echo "3. Download a GGUF model (e.g., from huggingface.co)"
    echo "4. Start server: ./server -m model.gguf --port 8080"
    echo ""
    echo "Example:"
    echo "  wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
    echo "  ./server -m llama-2-7b-chat.Q4_K_M.gguf --port 8080"
fi

# Setup LM Studio
echo ""
echo "🔄 Checking LM Studio..."

# Check if LM Studio server is available
if curl -s http://localhost:1234/v1/models > /dev/null 2>&1; then
    echo "✅ LM Studio server is running on http://localhost:1234"
    echo "📋 Available models in LM Studio:"
    curl -s http://localhost:1234/v1/models | grep -o '"id":"[^"]*"' | head -5 | sed 's/"id":"//;s/"//'
else
    echo "❌ LM Studio server not found on http://localhost:1234"
    echo ""
    echo "To set up LM Studio:"
    echo "1. Download from: https://lmstudio.ai/"
    echo "2. Install and launch LM Studio"
    echo "3. Download a model (Llama 2, Mistral, etc.)"
    echo "4. Go to 'Local Server' tab"
    echo "5. Select model and set port to 1234"
    echo "6. Click 'Start Server'"
fi

echo ""
echo "🎯 Configuration Summary:"
echo "OLLAMA_BASE_URL=http://localhost:11434"
echo "LM_STUDIO_BASE_URL=http://localhost:1234"
echo "LLAMACPP_BASE_URL=http://localhost:8080"
echo ""
echo "Ollama, LM Studio, and llama.cpp are now available as providers in Goblin Assistant!"
echo "Select 'ollama', 'lm_studio_local', or 'llamacpp' from the provider dropdown."
