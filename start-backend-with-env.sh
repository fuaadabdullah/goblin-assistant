#!/bin/bash
# Start the local backend for this workspace.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env.local ]; then
    set -a
    # shellcheck disable=SC1091
    source .env.local
    set +a
fi

# Default local development to SQLite so auth/chat work without a remote DB.
if [ "${GOBLIN_USE_REMOTE_DATABASE:-false}" != "true" ]; then
    export DATABASE_URL="${LOCAL_DATABASE_URL:-sqlite+aiosqlite:///./goblin_assistant.db}"
fi

exec python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8004 --reload
