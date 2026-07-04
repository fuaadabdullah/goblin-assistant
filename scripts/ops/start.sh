#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Goblin backend entrypoint"
echo "Repo root: ${REPO_ROOT}"

cd "${REPO_ROOT}"
exec env PYTHONPATH="${REPO_ROOT}/apps/api/src" \
  uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
