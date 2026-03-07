#!/usr/bin/env python3
"""Startup wrapper that catches and logs import/init errors.

Reports errors to a simple HTTP endpoint so we can see what's failing
when Render logs are not accessible via API.
"""
import sys
import os
import io
import traceback

log = io.StringIO()

def emit(msg):
    print(msg, flush=True)
    log.write(msg + "\n")

emit("=== START.PY: Beginning startup ===")
emit(f"Python version: {sys.version}")
emit(f"Working dir: {os.getcwd()}")
emit(f"Files in cwd: {os.listdir('.')[:20]}")

# Step 1: test basic imports one by one
for mod_name in [
    "fastapi", "uvicorn", "structlog", "httpx", "sqlalchemy",
    "redis", "sentry_sdk", "dotenv", "tomllib",
]:
    try:
        __import__(mod_name)
        emit(f"  OK: {mod_name}")
    except ImportError as e:
        emit(f"  FAIL: {mod_name} -> {e}")

# Step 2: test api submodule imports
for sub in [
    "api.providers.base",
    "api.providers.vertex_ai",
    "api.providers.aliyun",
    "api.providers.dispatcher_fixed",
    "api.services.provider_health",
]:
    try:
        __import__(sub)
        emit(f"  OK: {sub}")
    except Exception as e:
        emit(f"  FAIL: {sub} -> {type(e).__name__}: {e}")
        traceback.print_exc(file=log)

# Step 3: try the full import
try:
    emit("Importing api.main...")
    from api.main import app
    emit("Import successful!")
except Exception as e:
    emit(f"!!! IMPORT FAILED: {type(e).__name__}: {e}")
    traceback.print_exc(file=log)

# Step 4: write debug output to a file we can serve
debug_output = log.getvalue()
try:
    with open("/tmp/startup_debug.txt", "w") as f:
        f.write(debug_output)
except Exception:
    pass

# Step 5: If we have the app, start it; otherwise start a minimal debug server
try:
    app  # check if app was imported
except NameError:
    # App failed to import — start minimal server that shows the error
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class DebugHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(debug_output.encode())

    port = int(os.environ.get("PORT", "10000"))
    emit(f"Starting DEBUG server on port {port} (app failed to import)")
    server = HTTPServer(("0.0.0.0", port), DebugHandler)
    server.serve_forever()
else:
    import uvicorn
    port = int(os.environ.get("PORT", "10000"))
    emit(f"Starting uvicorn on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
