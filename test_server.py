#!/usr/bin/env python3
"""
Minimal MCP test server for endpoint testing.
"""

import uvicorn
from fastapi import FastAPI
from mcp_router import router as mcp_router

app = FastAPI(title="MCP Test Server")

# Include MCP router
app.include_router(mcp_router, prefix="/mcp/v1")


@app.get("/")
async def root():
    return {"message": "MCP Test Server", "status": "running"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
