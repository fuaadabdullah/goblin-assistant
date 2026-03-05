#!/bin/bash
# Goblin Assistant Backend Startup Script
# Ensures Ollama models are downloaded from Google Drive before starting

set -e

echo "🚀 Starting Goblin Assistant Backend..."

# Change to the project directory
cd "$(dirname "$0")"

# Ensure Ollama models are available from Google Drive
echo "⬇️  Ensuring Ollama models are downloaded from Google Drive..."
if [ -f "setup_ollama_from_drive.py" ]; then
    python3 setup_ollama_from_drive.py
else
    echo "⚠️  setup_ollama_from_drive.py not found, skipping model download"
fi

# Start Ollama service if not running and when OLLAMA_HOST targets localhost
echo "🔍 Checking Ollama deployment target..."
OLLAMA_HOST=${OLLAMA_HOST:-}
if [ -z "$OLLAMA_HOST" ] || [[ "$OLLAMA_HOST" =~ "127.0.0.1" ]] || [[ "$OLLAMA_HOST" =~ "localhost" ]] || [[ "$OLLAMA_HOST" =~ "http://127.0.0.1" ]] || [[ "$OLLAMA_HOST" =~ "http://localhost" ]]; then
    echo "📦 Ollama target is local or not configured; ensuring local Ollama is running..."
    if ! pgrep -x "ollama" > /dev/null; then
        echo "📦 Starting Ollama service..."
        nohup ollama serve > ollama.log 2>&1 &
        sleep 5  # Wait for Ollama to start
    else
        echo "✅ Ollama is already running"
    fi
else
    echo "🌐 Ollama is configured to run remotely at $OLLAMA_HOST; skipping local startup"
fi

# Verify models are available
echo "📋 Verifying available models..."
ollama list

# Start the canonical FastAPI backend
echo "🌐 Starting FastAPI backend (canonical)..."
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant/backend

if [ "$1" = "prod" ]; then
    echo "🏭 Starting in production mode with Uvicorn..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
else
    echo "🛠️  Starting in development mode (reload enabled)..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
