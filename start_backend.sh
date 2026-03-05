#!/bin/bash

# Start Goblin Assistant Backend with GCP LLM configuration

cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Load environment variables
export OLLAMA_GCP_URL=http://34.60.255.199:11434
export LLAMACPP_GCP_URL=http://34.132.226.143:8000

# Start the server
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8004
