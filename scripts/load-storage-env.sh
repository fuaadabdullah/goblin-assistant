#!/bin/bash
# Load GOBLINOS storage environment variables

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_ROOT/.env.storage" ]; then
    set -a
    source "$PROJECT_ROOT/.env.storage"
    set +a
    echo "✅ Loaded storage configuration from .env.storage"
    echo "   GOBLINOS_BASE: $GOBLINOS_BASE"
else
    echo "❌ ERROR: .env.storage not found"
    echo "   Run: ./scripts/setup-external-storage.sh"
    exit 1
fi
