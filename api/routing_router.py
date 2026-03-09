from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

try:
    from .routing.router import top_providers_for, route_task
except ImportError:
    # Fallback if routing module is not available
    def top_providers_for(
        capability: str,
        prefer_local: bool = False,
        prefer_cost: bool = False,
        limit: int = 6,
    ) -> List[str]:
        _ = (capability, prefer_local, prefer_cost, limit)
        return ["openai", "anthropic", "gemini", "ollama"]

    async def route_task(
        task_type: str,
        payload: Dict[str, Any],
        prefer_local: bool = False,
        prefer_cost: bool = False,
        max_retries: int = 2,
        stream: bool = False,
    ) -> Dict[str, Any]:
        _ = (task_type, payload, prefer_local, prefer_cost, max_retries, stream)
        await asyncio.sleep(0)
        return {"ok": False, "error": "Routing system not available", "fallback": True}

    def route_task_sync(*args, **kwargs) -> Dict[str, Any]:
        _ = (args, kwargs)
        return {"ok": False, "error": "Routing system not available"}


router = APIRouter(prefix="/routing", tags=["routing"])


class RouteRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    prefer_local: Optional[bool] = False
    prefer_cost: Optional[bool] = False
    max_retries: Optional[int] = 2
    stream: Optional[bool] = False


class ProviderInfo(BaseModel):
    name: str
    capabilities: List[str]
    models: List[str]
    priority_tier: int
    cost_score: float
    bandwidth_score: float


@router.get("/providers", response_model=List[str])
async def get_available_providers():
    """Get list of all configured providers"""
    try:
        # Return providers that have valid API keys configured
        providers = []
        for capability in ["chat", "reasoning", "code"]:
            candidates = top_providers_for(capability)
            print(f"DEBUG: Capability {capability}, candidates: {candidates}")
            providers.extend(candidates)
        result = list(set(providers))  # Remove duplicates
        print(f"DEBUG: Final providers: {result}")
        return result
    except (RuntimeError, ValueError, TypeError):
        print("DEBUG: Exception in get_available_providers")
        # Fallback to basic providers if routing system fails
        return [
            "openai",
            "anthropic",
            "gemini",
            "ollama",
            "groq",
            "deepseek",
            "siliconeflow",
        ]


@router.get("/providers/{capability}", response_model=List[str])
async def get_providers_for_capability(capability: str):
    """Get providers that support a specific capability"""
    try:
        return top_providers_for(capability)
    except (RuntimeError, ValueError, TypeError):
        return ["openai", "anthropic"]  # Fallback


@router.post("/route")
async def route_request(request: RouteRequest):
    """Route a task to the best available provider.

    Provider selection algorithm considers:
    - Performance vs cost optimization flags
    - Local vs cloud provider preference
    - Retry logic with exponential backoff
    - Provider health and availability status
    """
    try:
        # Call the async route_task function directly
        # The router module handles provider selection based on capabilities
        # and optimization preferences (prefer_local, prefer_cost)
        result = await route_task(
            task_type=request.task_type,
            payload=request.payload,
            prefer_local=bool(request.prefer_local),
            prefer_cost=bool(request.prefer_cost),
            max_retries=int(request.max_retries or 2),
            stream=bool(request.stream),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}") from e
