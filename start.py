#!/usr/bin/env python3
"""Startup wrapper that catches and logs import/init errors."""
import sys
import os
import traceback

print("=== START.PY: Beginning startup ===", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Working dir: {os.getcwd()}", flush=True)

try:
    print("Importing api.main...", flush=True)
    from api.main import app
    print("Import successful!", flush=True)
except Exception as e:
    print(f"!!! IMPORT FAILED: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

# If import succeeds, start uvicorn normally
import uvicorn

port = int(os.environ.get("PORT", "10000"))
print(f"Starting uvicorn on port {port}...", flush=True)
uvicorn.run(app, host="0.0.0.0", port=port)
