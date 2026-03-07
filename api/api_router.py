from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import asyncio
import time
import os
from .core.orchestration import create_simple_orchestration_plan
from .write_time_router import router as write_time_router
from .providers.dispatcher_fixed import invoke_provider, dispatcher

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/debug/aliyun")
async def debug_aliyun():
    """Temporary debug endpoint - remove after fixing aliyun."""
    ds_key = os.getenv("DASHSCOPE_API_KEY", "")
    config = dispatcher._get_provider_config("aliyun")
    provider = dispatcher.get_provider("aliyun")
    return {
        "env_var_set": bool(ds_key),
        "env_var_len": len(ds_key),
        "env_var_prefix": ds_key[:8] if ds_key else "",
        "config_api_key_env": config.get("api_key_env"),
        "provider_type": type(provider).__name__,
        "provider_api_key_env": getattr(provider, "api_key_env", None),
        "provider_cached_key_len": len(getattr(provider, "api_key", "") or ""),
        "provider_get_api_key_len": len(provider._get_api_key()),
    }


# ============================================================================
# Simple Chat Endpoint - Routes to Kamatera LLM
# ============================================================================


class SimpleChatMessage(BaseModel):
    role: str
    content: str


class SimpleChatRequest(BaseModel):
    messages: List[SimpleChatMessage]
    model: Optional[str] = None
    provider: Optional[str] = (
        None  # Allow specifying provider (e.g., "ollama_gcp", "llamacpp_gcp")
    )
    stream: Optional[bool] = False


class SimpleChatResponse(BaseModel):
    ok: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


@router.post("/chat", response_model=SimpleChatResponse)
async def simple_chat(request: SimpleChatRequest):
    """
    Simple chat endpoint that routes to GCP LLM providers.

    This is the main endpoint for the frontend to use for chat functionality.
    It defaults to the GCP Ollama server with qwen2.5:3b model.

    Example:
        POST /api/chat
        {
            "messages": [{"role": "user", "content": "Hello!"}]
        }
    """
    try:
        # Convert messages to dict format
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # Use auto-selection when provider not specified (smart routing with fallback)
        # When explicitly specified, use that provider directly
        provider = request.provider or "auto"
        model = request.model  # Let dispatcher pick default model if None

        # Create payload for provider
        payload = {
            "messages": messages,
            "model": model,
        }

        # Invoke provider
        response = await invoke_provider(
            pid=provider,
            model=model,
            payload=payload,
            timeout_ms=30000,
            stream=request.stream,
        )

        if isinstance(response, dict) and response.get("ok"):
            # Extract text from provider response
            # Standard format: {"ok": True, "result": {"text": ..., "raw": ...}}
            result_data = response.get("result", {})
            if isinstance(result_data, dict) and result_data.get("text"):
                text = result_data["text"]
            else:
                # Fallback: some providers put text at top level
                text = response.get("text", "")
            return SimpleChatResponse(
                ok=True,
                result={"text": text} if text else result_data,
                provider=response.get("provider", "unknown"),
                model=response.get("model", "unknown"),
            )
        else:
            error_msg = (
                response.get("error", "Unknown error")
                if isinstance(response, dict)
                else str(response)
            )
            return SimpleChatResponse(
                ok=False,
                error=error_msg,
            )

    except Exception as e:
        return SimpleChatResponse(
            ok=False,
            error=str(e),
        )


# ============================================================================
# Original API Router Endpoints
# ============================================================================


class RouteTaskRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    prefer_local: Optional[bool] = False
    prefer_cost: Optional[bool] = False
    max_retries: Optional[int] = 2
    stream: Optional[bool] = False


class StreamTaskRequest(BaseModel):
    goblin: str
    task: str
    code: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class StreamResponse(BaseModel):
    stream_id: str
    status: str = "started"


# In-memory storage for streams (in production, use Redis or database)
# Production implementation would use Redis for distributed stream management
# or a message queue system (RabbitMQ, Apache Kafka) for scalability
ACTIVE_STREAMS = {}


@router.post("/route_task")
async def route_task(request: RouteTaskRequest):
    """Route a task to the best available provider"""
    try:
        # For now, return a simple success response
        # In production, this would delegate to the routing system
        return {
            "ok": True,
            "message": "Task routed successfully",
            "task_id": str(uuid.uuid4()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@router.post("/route_task_stream_start")
async def start_stream_task(request: StreamTaskRequest):
    """Start a streaming task"""
    try:
        stream_id = str(uuid.uuid4())

        # Store stream information
        ACTIVE_STREAMS[stream_id] = {
            "goblin": request.goblin,
            "task": request.task,
            "code": request.code,
            "provider": request.provider,
            "model": request.model,
            "status": "running",
            "chunks": [],
            "created_at": time.time(),
        }

        # Simulate task execution (in production, this would queue the task)
        asyncio.create_task(simulate_stream_task(stream_id))

        return StreamResponse(stream_id=stream_id, status="started")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start stream task: {str(e)}"
        )


@router.get("/route_task_stream_poll/{stream_id}")
async def poll_stream_task(stream_id: str):
    """Poll for streaming task updates"""
    if stream_id not in ACTIVE_STREAMS:
        raise HTTPException(status_code=404, detail="Stream not found")

    stream = ACTIVE_STREAMS[stream_id]

    # Return available chunks
    chunks = stream.get("chunks", [])
    stream["chunks"] = []  # Clear processed chunks

    return {
        "stream_id": stream_id,
        "status": stream["status"],
        "chunks": chunks,
        "done": stream["status"] == "completed",
    }


@router.post("/route_task_stream_cancel/{stream_id}")
async def cancel_stream_task(stream_id: str):
    """Cancel a streaming task"""
    if stream_id not in ACTIVE_STREAMS:
        raise HTTPException(status_code=404, detail="Stream not found")

    ACTIVE_STREAMS[stream_id]["status"] = "cancelled"

    return {"stream_id": stream_id, "status": "cancelled"}


async def simulate_stream_task(stream_id: str):
    """Simulate streaming task execution"""
    await asyncio.sleep(1)  # Initial delay

    if stream_id not in ACTIVE_STREAMS:
        return

    stream = ACTIVE_STREAMS[stream_id]
    response_text = (
        f"Executed task '{stream['task']}' using goblin '{stream['goblin']}'"
    )

    # Simulate streaming chunks
    words = response_text.split()
    for i, word in enumerate(words):
        await asyncio.sleep(0.1)  # Simulate processing delay

        if stream["status"] == "cancelled":
            break

        chunk = {
            "content": word + (" " if i < len(words) - 1 else ""),
            "token_count": len(word) // 4 + 1,
            "cost_delta": 0.001,
            "done": False,
        }

        stream["chunks"].append(chunk)

    # Mark as completed
    if stream["status"] != "cancelled":
        stream["status"] = "completed"
        stream["chunks"].append(
            {
                "result": response_text,
                "cost": len(words) * 0.001,
                "tokens": sum(len(word) for word in words) // 4,
                "done": True,
            }
        )


@router.get("/goblins")
async def get_goblins():
    """Get list of available goblins"""
    # Mock goblin data - in production, this would come from a database
    goblins = [
        {
            "id": "docs-writer",
            "name": "docs-writer",
            "title": "Documentation Writer",
            "status": "available",
            "guild": "Crafters",
        },
        {
            "id": "code-writer",
            "name": "code-writer",
            "title": "Code Writer",
            "status": "available",
            "guild": "Crafters",
        },
        {
            "id": "search-goblin",
            "name": "search-goblin",
            "title": "Search Specialist",
            "status": "available",
            "guild": "Huntress",
        },
        {
            "id": "analyze-goblin",
            "name": "analyze-goblin",
            "title": "Data Analyst",
            "status": "available",
            "guild": "Mages",
        },
    ]
    return goblins


@router.get("/history/{goblin_id}")
async def get_goblin_history(goblin_id: str, limit: int = 10):
    """Get task history for a specific goblin"""
    # Mock history data - in production, this would come from a database
    mock_history = [
        {
            "id": f"task_{i}",
            "goblin": goblin_id,
            "task": f"Sample task {i}",
            "response": f"Completed task {i} successfully",
            "timestamp": time.time() - (i * 3600),  # Hours ago
            "kpis": f"duration_ms:{1000 + i * 100},cost:{0.01 * (i + 1)}",
        }
        for i in range(min(limit, 20))
    ]
    return mock_history


@router.get("/stats/{goblin_id}")
async def get_goblin_stats(goblin_id: str):
    """Get statistics for a specific goblin"""
    # Mock stats - in production, this would be calculated from actual data
    return {
        "goblin_id": goblin_id,
        "total_tasks": 42,
        "total_cost": 1.23,
        "avg_duration_ms": 2500,
        "success_rate": 0.95,
        "last_active": time.time() - 3600,  # 1 hour ago
    }


class ParseOrchestrationRequest(BaseModel):
    text: str
    default_goblin: Optional[str] = None


@router.post("/orchestrate/parse")
async def parse_orchestration(request: ParseOrchestrationRequest):
    """Parse natural language into orchestration plan"""
    return create_simple_orchestration_plan(request.text, request.default_goblin)


@router.post("/orchestrate/execute")
async def execute_orchestration(plan_id: str):
    """Execute an orchestration plan"""
    # Mock execution - in production, this would trigger actual orchestration
    return {
        "execution_id": str(uuid.uuid4()),
        "plan_id": plan_id,
        "status": "started",
        "estimated_completion": time.time() + 300,  # 5 minutes from now
    }


@router.get("/orchestrate/plans/{plan_id}")
async def get_orchestration_plan(plan_id: str):
    """Get details of an orchestration plan"""
    # Mock plan data
    return {
        "plan_id": plan_id,
        "status": "completed",
        "steps": [
            {
                "id": "step1",
                "goblin": "docs-writer",
                "task": "Document the code",
                "status": "completed",
                "duration_ms": 1500,
                "cost": 0.02,
            }
        ],
        "total_cost": 0.02,
        "total_duration_ms": 1500,
        "created_at": time.time() - 3600,
    }
