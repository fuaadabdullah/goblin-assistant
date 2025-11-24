#!/usr/bin/env python3
"""
Minimal FastAPI app for testing Datadog monitoring
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'api/fastapi'))

# Import monitoring components
from logging_config import logger
from metrics import metrics
from ddtrace_config import goblin_tracer

# Set environment variables for Datadog
os.environ.setdefault("DD_API_KEY", "597e545d68c3bf13d3d138be41f2d62e")
os.environ.setdefault("DD_APP_KEY", "597e545d68c3bf13d3d138be41f2d62e")
os.environ.setdefault("DD_ENV", "dev")
os.environ.setdefault("DD_SERVICE", "goblin-assistant-api")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

app = FastAPI(title="Goblin Assistant API", version="1.0.0")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Goblin Assistant API", "status": "monitoring_enabled"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "monitoring": "active"}

@app.post("/invoke")
async def invoke(request: Request):
    """Mock invoke endpoint with monitoring"""
    start_time = time.time()

    try:
        # Simulate some processing
        await request.json()

        # Record metrics
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_request("/invoke", "POST", 200, duration_ms)
        metrics.record_llm_call("openai", "gpt-4o", tokens=150, cost_usd=0.002)

        # Log the request
        logger.info("Request processed", extra={"context": {"endpoint": "/invoke", "duration_ms": duration_ms}})

        return {"result": "success", "tokens": 150, "cost": 0.002}

    except Exception as e:
        # Record error metrics
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_request("/invoke", "POST", 500, duration_ms)
        metrics.record_provider_error("openai", "processing_error")

        logger.error("Request failed", extra={"context": {"error": str(e)}})
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.get("/metrics")
async def get_metrics():
    """Get current metrics summary"""
    return {
        "status": "monitoring_active",
        "datadog_agent": "configured",
        "service": "goblin-assistant-api",
        "env": "dev"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Goblin Assistant API with Datadog monitoring...")
    print("📊 Metrics will be sent to Datadog")
    print("📝 Logs will be sent to Datadog")
    print("🔍 APM traces will be collected")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
