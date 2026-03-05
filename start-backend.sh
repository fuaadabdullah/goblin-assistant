#!/bin/bash
# Start Goblin Assistant backend with proper environment

cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Load .env.local into environment
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Start backend
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8004 --reload
