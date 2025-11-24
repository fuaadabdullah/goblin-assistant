"""
FastAPI adapter for Goblin Assistant.
Provides REST and WebSocket endpoints for RAG queries and streaming.
"""

import os
import asyncio
import hashlib
import time
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

from ..providers.base import BaseProvider
from ..indexer.indexer import VectorIndexer
from .router import ProviderRouter
from .rag import RAGSystem
from .datadog_metrics import MetricsCollector


# Global instances
indexer = None
router = None
rag_system = None
metrics = None

security = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global indexer, router, rag_system, metrics

    # Startup
    print("🚀 Starting Goblin Assistant FastAPI adapter...")

    # Initialize components
    indexer = VectorIndexer()
    router = ProviderRouter()
    rag_system = RAGSystem(indexer=indexer, router=router)
    metrics = MetricsCollector()

    # Load index if exists
    try:
        await indexer.load_index()
        print("✅ Index loaded successfully")
    except Exception as e:
        print(f"⚠️  No existing index found: {e}")

    yield

    # Shutdown
    print("🛑 Shutting down Goblin Assistant...")
    if indexer:
        await indexer.save_index()


app = FastAPI(
    title="Goblin Assistant API",
    description="Hybrid Continue integration with local RAG and provider routing",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Extract and hash user ID from JWT token or use anonymous."""
    if credentials:
        # In production, validate JWT and extract user ID
        # For now, hash the token as user identifier
        user_id = hashlib.sha256(credentials.credentials.encode()).hexdigest()[:16]
    else:
        user_id = "anonymous"

    return user_id


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "components": {
            "indexer": indexer is not None,
            "router": router is not None,
            "rag_system": rag_system is not None,
            "metrics": metrics is not None,
        },
    }


@app.post("/assistant/query")
async def rag_query(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    """
    Synchronous RAG query endpoint.
    Returns complete response with retrieved context.
    """
    start_time = time.time()

    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Get RAG response
        response = await rag_system.query(query, user_id=user_id)

        # Record metrics
        latency_ms = (time.time() - start_time) * 1000
        background_tasks.add_task(
            metrics.record_rag_request,
            user_id=user_id,
            latency_ms=latency_ms,
            hit_rate=response.get("hit_rate", 0),
            tokens_used=response.get("usage", {}).get("total_tokens", 0),
        )

        return response

    except Exception as e:
        # Record error metrics
        background_tasks.add_task(
            metrics.record_error,
            user_id=user_id,
            error_type=type(e).__name__,
            endpoint="/assistant/query",
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/assistant/stream")
async def rag_stream(websocket: WebSocket, user_id: str = Depends(get_user_id)):
    """
    WebSocket endpoint for streaming RAG responses.
    Sends chunks as they become available.
    """
    await websocket.accept()

    try:
        # Receive initial query
        data = await websocket.receive_json()
        query = data.get("query", "")

        if not query:
            await websocket.send_json({"error": "Query is required"})
            await websocket.close()
            return

        start_time = time.time()

        # Stream RAG response
        async for chunk in rag_system.stream_query(query, user_id=user_id):
            await websocket.send_json(chunk)

        # Send completion signal
        latency_ms = (time.time() - start_time) * 1000
        await websocket.send_json({"type": "complete", "latency_ms": latency_ms})

    except Exception as e:
        await websocket.send_json({"error": str(e), "type": "error"})
    finally:
        await websocket.close()


@app.post("/continue/hook")
async def continue_hook(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    """
    Continue extension integration endpoint.
    Handles IDE chat, autocomplete, and workflow requests.
    """
    start_time = time.time()

    try:
        action = request.get("action", "")
        payload = request.get("payload", {})

        if action == "chat":
            # Handle chat messages
            response = await rag_system.query(
                payload.get("message", ""),
                user_id=user_id,
                context=payload.get("context", {}),
            )

        elif action == "autocomplete":
            # Handle autocomplete requests
            response = await rag_system.query(
                payload.get("prefix", ""), user_id=user_id, task_type="code_completion"
            )

        elif action == "workflow":
            # Handle workflow execution
            response = await rag_system.execute_workflow(
                payload.get("workflow", {}), user_id=user_id
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        # Record workflow metrics
        latency_ms = (time.time() - start_time) * 1000
        background_tasks.add_task(
            metrics.record_workflow_run,
            user_id=user_id,
            action=action,
            latency_ms=latency_ms,
            accepted=True,
        )

        return response

    except Exception as e:
        # Record error metrics
        background_tasks.add_task(
            metrics.record_workflow_run,
            user_id=user_id,
            action=request.get("action", "unknown"),
            accepted=False,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index/webhook")
async def index_webhook(request: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    CI/GitHub webhook for re-indexing changed files.
    """
    try:
        # Validate webhook (in production, check signature)
        changes = request.get("changes", [])
        repo = request.get("repository", "unknown")

        if not changes:
            return {"status": "no_changes"}

        # Trigger incremental indexing
        background_tasks.add_task(indexer.index_changes, changes=changes, repo=repo)

        return {"status": "indexing_started", "changes": len(changes)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Get current metrics (for debugging)."""
    return await metrics.get_summary()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True, log_level="info")
