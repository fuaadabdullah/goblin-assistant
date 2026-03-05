"""
Routing Analytics Router

Provides API endpoints for monitoring AI provider routing:
- Provider health status
- Routing decisions history
- Cost tracking
- Performance metrics
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

# Import services (graceful fallback if not available)
try:
    from api.services.smart_router import smart_router
    from api.services.provider_health import health_monitor

    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False
    smart_router = None
    health_monitor = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routing", tags=["routing-analytics"])


@router.get("/health")
async def get_provider_health() -> Dict[str, Any]:
    """
    Get health status of all AI providers.

    Returns:
        Dict with provider health information including:
        - status (healthy/degraded/unhealthy/unknown)
        - average latency
        - last check time
        - consecutive failures
    """
    if not SERVICES_AVAILABLE or health_monitor is None:
        return {
            "available": False,
            "message": "Health monitoring service not available",
        }

    return {
        "available": True,
        "providers": health_monitor.get_all_status(),
        "healthy_providers": health_monitor.get_healthy_providers(),
        "best_providers": health_monitor.get_best_providers(),
    }


@router.get("/health/{provider_id}")
async def get_provider_health_detail(provider_id: str) -> Dict[str, Any]:
    """
    Get detailed health status for a specific provider.

    Args:
        provider_id: Provider identifier (e.g., 'ollama_gcp', 'openai')

    Returns:
        Detailed health information for the provider
    """
    if not SERVICES_AVAILABLE or health_monitor is None:
        raise HTTPException(
            status_code=503, detail="Health monitoring service not available"
        )

    status = health_monitor.get_status(provider_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    return status


@router.get("/costs")
async def get_cost_tracking() -> Dict[str, Any]:
    """
    Get current cost tracking status.

    Returns:
        Dict with cost tracking information including:
        - hourly budget
        - current spend
        - remaining budget
        - request count
    """
    if not SERVICES_AVAILABLE or smart_router is None:
        return {
            "available": False,
            "message": "Smart routing service not available",
        }

    return {
        "available": True,
        **smart_router.cost_tracker.get_status(),
    }


@router.get("/status")
async def get_routing_status() -> Dict[str, Any]:
    """
    Get overall routing system status.

    Returns:
        Comprehensive status of the routing system including:
        - Current routing strategy
        - Healthy providers
        - Cost tracking
        - Best available providers
    """
    if not SERVICES_AVAILABLE or smart_router is None:
        return {
            "available": False,
            "message": "Smart routing service not available",
            "fallback_mode": True,
        }

    return {
        "available": True,
        **smart_router.get_status(),
    }


@router.get("/strategies")
async def list_routing_strategies() -> Dict[str, Any]:
    """
    List available routing strategies.

    Returns:
        Dict with available routing strategies and their descriptions
    """
    return {
        "strategies": [
            {
                "id": "cost_optimized",
                "name": "Cost Optimized",
                "description": "Prioritize free and cheap providers (GCP local → Groq → Cloud)",
                "priority_order": [
                    "ollama_gcp",
                    "llamacpp_gcp",
                    "groq",
                    "siliconeflow",
                    "deepseek",
                    "openai",
                    "anthropic",
                ],
            },
            {
                "id": "quality_first",
                "name": "Quality First",
                "description": "Prioritize high-quality providers (Claude → GPT-4 → Cloud)",
                "priority_order": [
                    "anthropic",
                    "openai",
                    "groq",
                    "deepseek",
                    "ollama_gcp",
                ],
            },
            {
                "id": "latency_optimized",
                "name": "Latency Optimized",
                "description": "Prioritize fastest providers (Groq → GCP → Cloud)",
                "priority_order": ["groq", "ollama_gcp", "openai", "anthropic"],
            },
            {
                "id": "local_first",
                "name": "Local First",
                "description": "Prioritize local/self-hosted providers for privacy",
                "priority_order": ["ollama_gcp", "llamacpp_gcp", "groq", "openai"],
            },
            {
                "id": "balanced",
                "name": "Balanced",
                "description": "Balance between cost, quality, and latency",
                "priority_order": [
                    "groq",
                    "ollama_gcp",
                    "deepseek",
                    "openai",
                    "anthropic",
                ],
            },
        ],
        "default": "cost_optimized",
    }


@router.get("/providers")
async def list_available_providers() -> Dict[str, Any]:
    """
    List all configured AI providers.

    Returns:
        Dict with provider information including:
        - Provider ID and name
        - Capabilities
        - Cost information
        - Health status
    """
    providers_info = {
        "ollama_gcp": {
            "name": "GCP Ollama",
            "type": "local",
            "capabilities": ["chat", "code", "reasoning"],
            "models": ["qwen2.5:3b", "llama3.2:1b"],
            "cost_per_1k_tokens": {"input": 0, "output": 0},
            "notes": "Free self-hosted on GCP",
        },
        "llamacpp_gcp": {
            "name": "GCP llama.cpp",
            "type": "local",
            "capabilities": ["chat", "code"],
            "models": ["qwen2.5-3b-instruct-q4_k_m"],
            "cost_per_1k_tokens": {"input": 0, "output": 0},
            "notes": "Free self-hosted on GCP",
        },
        "groq": {
            "name": "Groq",
            "type": "cloud",
            "capabilities": ["chat", "code", "reasoning"],
            "models": ["llama-3.1-8b-instant", "mixtral-8x7b"],
            "cost_per_1k_tokens": {"input": 0.05, "output": 0.10},
            "notes": "Very fast inference",
        },
        "siliconeflow": {
            "name": "SiliconeFlow",
            "type": "cloud",
            "capabilities": ["chat", "code"],
            "models": ["Qwen/Qwen2.5-7B-Instruct"],
            "cost_per_1k_tokens": {"input": 0.01, "output": 0.03},
            "notes": "Budget-friendly",
        },
        "deepseek": {
            "name": "DeepSeek",
            "type": "cloud",
            "capabilities": ["chat", "code", "reasoning"],
            "models": ["deepseek-chat", "deepseek-coder"],
            "cost_per_1k_tokens": {"input": 0.14, "output": 0.28},
            "notes": "Excellent for code generation",
        },
        "openai": {
            "name": "OpenAI",
            "type": "cloud",
            "capabilities": [
                "chat",
                "code",
                "reasoning",
                "vision",
                "embedding",
                "image",
            ],
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            "cost_per_1k_tokens": {"input": 0.50, "output": 1.50},
            "notes": "GPT-4o-mini default",
        },
        "anthropic": {
            "name": "Anthropic",
            "type": "cloud",
            "capabilities": ["chat", "code", "reasoning", "vision"],
            "models": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"],
            "cost_per_1k_tokens": {"input": 3.00, "output": 15.00},
            "notes": "Claude 3.5 Sonnet default - premium quality",
        },
        "google": {
            "name": "Google Gemini",
            "type": "cloud",
            "capabilities": ["chat", "code", "reasoning", "vision"],
            "models": ["gemini-pro", "gemini-pro-vision"],
            "cost_per_1k_tokens": {"input": 0.35, "output": 1.05},
            "notes": "Gemini Pro",
        },
    }

    # Add health status if available
    if SERVICES_AVAILABLE and health_monitor is not None:
        for provider_id, info in providers_info.items():
            info["health"] = health_monitor.get_status(provider_id)

    return {
        "providers": providers_info,
        "disabled_providers": {
            "ollama_kamatera": "Unreachable since 2026-01-11",
            "llamacpp_kamatera": "Unreachable since 2026-01-11",
        },
    }


@router.post("/test/{provider_id}")
async def test_provider(provider_id: str) -> Dict[str, Any]:
    """
    Test a specific provider with a simple request.

    Args:
        provider_id: Provider to test

    Returns:
        Test result with latency and response
    """
    if not SERVICES_AVAILABLE or health_monitor is None:
        raise HTTPException(
            status_code=503, detail="Health monitoring service not available"
        )

    # Trigger a health check for this provider
    base_url, endpoint = health_monitor.HEALTH_ENDPOINTS.get(provider_id, (None, None))

    if base_url is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    # Run health check
    await health_monitor._check_provider(provider_id, base_url, endpoint, None)

    return health_monitor.get_status(provider_id)
