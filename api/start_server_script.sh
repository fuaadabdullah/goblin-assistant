#!/bin/bash
# Start the canonical FastAPI backend entrypoint
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}"
cd "${REPO_ROOT}"
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
