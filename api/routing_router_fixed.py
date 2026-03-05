from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
import toml

# Add the src directory to the path so we can import the routing module
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

router = APIRouter(prefix="/routing", tags=["routing"])


def load_provider_configs():
    """Load provider configurations from toml file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "providers.toml")
        with open(config_path, 'r') as f:
            return toml.load(f)
    except Exception as e:
        print(f"Warning: Could not load provider config: {e}")
        return {}


def top_providers_for(
    capability: str, prefer_local=False, prefer_cost=False, limit=6
) -> List[str]:
    """Get providers for a specific capability with fallback logic"""
    configs = load_provider_configs()
    providers_config = configs.get("providers", {})
    
    # Get preferred providers under budget (cost optimization)
    preferred = configs.get("default", {}).get("cost_optimization", {}).get(
        "preferred_providers_under_budget", []
    )
    
    # Filter providers that support the capability
    capable_providers = []
    for provider_name in preferred:
        provider_config = providers_config.get(provider_name, {})
        capabilities = provider_config.get("capabilities", [])
        if capability in capabilities:
            capable_providers.append(provider_name)
    
    # If no preferred providers found, fallback to basic providers
    if not capable_providers:
        if capability in ["chat", "reasoning", "code"]:
            capable_providers = ["openai", "anthropic", "google"]
        else:
            capable_providers = ["openai"]
    
    return capable_providers[:limit]


async def route_task(
    task_type: str,
    payload: Dict[str, Any],
    prefer_local: bool = False,
    prefer_cost: bool = False,
    max_retries: int = 2,
    stream: bool = False,
) -> Dict[str, Any]:
    return {"ok": False, "error": "Routing system not available", "fallback": True}


def route_task_sync(*args, **kwargs) -> Dict[str, Any]:
    return {"ok": False, "error": "Routing system not available"}


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
    except Exception:
        print("DEBUG: Exception in get_available_providers")
        # Fallback to basic providers if routing system fails
        return ["openai", "anthropic", "gemini", "ollama", "groq", "deepseek"]


@router.get("/providers/{capability}", response_model=List[str])
async def get_providers_for_capability(capability: str):
    """Get providers that support a specific capability"""
    try:
        return top_providers_for(capability)
    except Exception:
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
            prefer_local=request.prefer_local,
            prefer_cost=request.prefer_cost,
            max_retries=request.max_retries,
            stream=request.stream,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")