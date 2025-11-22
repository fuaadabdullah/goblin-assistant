#!/usr/bin/env bash
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f ".venv311/bin/activate" ]]; then
    source .venv311/bin/activate
fi

echo "Installing fastapi dev dependencies to local venv ..."
python3.11 -m venv .venv311 || true
source .venv311/bin/activate
pip install -r requirements.txt

echo "Starting FastAPI runtime on http://127.0.0.1:3001"
uvicorn app:app --reload --port 3001 --host 127.0.0.1
