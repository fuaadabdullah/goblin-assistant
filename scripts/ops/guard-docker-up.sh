#!/usr/bin/env bash
# Guard script: kill stale docker compose processes before launching new ones.
#
# Problem: `make api-docker-up` can spawn competing `docker compose` processes
# that displace healthy containers.  This script ensures only one build/up
# cycle is in flight at a time by killing stale processes first.
#
# Usage:  bash scripts/ops/guard-docker-up.sh

set -euo pipefail

echo "==> Guard: checking for stale docker compose processes..."

# Find PIDs of any running docker compose / docker-compose processes.
PIDS="$(pgrep -f 'docker[ -]compose' 2>/dev/null || true)"

if [ -n "${PIDS}" ]; then
    echo "    Found stale docker compose process(es): ${PIDS}"
    echo "    Killing..."
    # Kill stale processes.  Use -9 to ensure they die immediately.
    echo "${PIDS}" | xargs kill -9 2>/dev/null || true
    sleep 2
    echo "    Stale processes killed."
else
    echo "    No stale docker compose processes found."
fi

# Stop any existing backend container so the new launch doesn't fight it
# for the port or container name.
echo "==> Guard: stopping existing backend container (if running)..."
docker compose stop goblin-assistant-backend 2>/dev/null || true

echo "==> Guard: clear - ready for clean docker compose launch."