#!/bin/bash
# Start backend with proper environment variable loading

cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Load additional variables from .env.local if it exists
if [ -f .env.local ]; then
    # Export variables from .env.local (excluding comments and empty lines)
    set -a
    source <(grep -v '^#' .env.local | grep -v '^$' | sed 's/^export //g')
    set +a
fi

# Start the backend
exec python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8004 --reload
