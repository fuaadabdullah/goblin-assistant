#!/usr/bin/env bash
set -euo pipefail

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Goblin backend entrypoint"
# Print a quick directory listing and python path for debugging
echo "Working dir: $(pwd)"
ls -la /app || true
if [ -d /app/api ]; then
  echo "api directory exists"
  ls -la /app/api || true
else
  echo "WARNING: /app/api not found"
fi
python -c 'import sys; print("PYTHONPATH:", sys.path)'
python -c 'import importlib, pkgutil; print("Installed packages sample:", [p.name for p in pkgutil.iter_modules()][:10])'

# Start uvicorn with the expected import
# NOTE: this uses uvicorn api.main:app — change if your package name differs
cd /app
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8001}
