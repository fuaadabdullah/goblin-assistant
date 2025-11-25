#!/usr/bin/env python3
"""
Minimal MCP test server for testing MCP functionality without full app dependencies.
"""

import asyncio
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add current directory to path
sys.path.append(".")

# Import only the auth service for testing
from mcp_auth import AuthService

# Create minimal FastAPI app
app = FastAPI(title="MCP Test Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize auth service
auth_service = AuthService()


@app.get("/")
async def root():
    return {"message": "MCP Test Server", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/mcp/v1/auth/login")
async def login(username: str, password: str):
    """Simple login endpoint for testing."""
    user = auth_service.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = auth_service.create_access_token(
        {"sub": user.username, "role": user.role.value}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": user.username, "role": user.role.value},
    }


@app.get("/mcp/v1/admin/dashboard")
async def dashboard():
    """Mock dashboard endpoint."""
    return {
        "total_requests": 0,
        "active_requests": 0,
        "completed_requests": 0,
        "failed_requests": 0,
        "providers": {
            "openai": {"status": "healthy", "requests": 0},
            "anthropic": {"status": "healthy", "requests": 0},
            "local": {"status": "healthy", "requests": 0},
        },
    }


if __name__ == "__main__":
    print("🚀 Starting MCP Test Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
