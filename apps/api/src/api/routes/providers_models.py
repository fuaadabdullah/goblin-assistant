"""Provider and model registry backed by the authoritative dispatcher."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from api.core.contracts import SuccessEnvelope
from api.core.errors import DomainError
from api.providers.dispatcher import dispatcher
from api.providers.router_service import ROUTER_PROVIDER_ID, summarize_router_models

router = APIRouter(tags=["providers"])


def _provider_models(entry: Dict[str, Any]) -> List[str]:
    models = list(entry.get("models", []))
    default_model = str(entry.get("default_model", "")).strip()
    if default_model and default_model not in models:
        models.append(default_model)
    return sorted({model for model in models if model})


def _router_model_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": entry["name"],
        "provider": ROUTER_PROVIDER_ID,
        "provider_id": ROUTER_PROVIDER_ID,
        "size": None,
        "health": entry.get("health", "unknown"),
        "is_selectable": bool(entry.get("is_selectable")),
        "health_reason": entry.get("health_reason"),
        "description": entry.get("description"),
        "routing_strategy": entry.get("routing_strategy"),
        "num_retries": entry.get("num_retries"),
        "enable_pre_call_checks": entry.get("enable_pre_call_checks"),
        "fallbacks": entry.get("fallbacks", []),
        "context_window_fallbacks": entry.get("context_window_fallbacks", []),
        "content_policy_fallbacks": entry.get("content_policy_fallbacks", []),
        "backends": entry.get("backends", []),
    }


@router.get(
    "/providers/models",
    response_model=SuccessEnvelope[Dict[str, Any]],
    openapi_extra={"x-goblin-route-contract": "canonical-routing-inventory"},
)
async def get_provider_models() -> SuccessEnvelope[Dict[str, Any]]:
    """Canonical provider and logical-router inventory surface."""
    try:
        inventory = await dispatcher.get_provider_inventory(include_hidden=False)
        providers: List[Dict[str, Any]] = []
        models: List[Dict[str, Any]] = []
        router_models = summarize_router_models()
        router_model_rows: List[Dict[str, Any]] = []

        for entry in inventory:
            provider_id = entry["id"]
            provider_models = _provider_models(entry)
            provider_health = str(entry.get("health", "unknown"))
            selectable = bool(entry.get("is_selectable"))
            health_reason = entry.get("health_reason")

            providers.append(
                {
                    "id": provider_id,
                    "health": provider_health,
                    "configured": bool(entry.get("configured")),
                    "is_selectable": selectable,
                    "health_reason": health_reason,
                }
            )

            for model_name in provider_models:
                models.append(
                    {
                        "name": model_name,
                        "provider": provider_id,
                        "provider_id": provider_id,
                        "size": None,
                        "health": provider_health,
                        "is_selectable": selectable,
                        "health_reason": health_reason,
                    }
                )

        for entry in router_models:
            router_model_rows.append(_router_model_entry(entry))

        return SuccessEnvelope(
            data={
                "models": models + router_model_rows,
                "providers": providers,
                "router_models": router_models,
                "source": "configured_with_health_plus_router",
                "total_models": len(models) + len(router_model_rows),
                "total_providers": len(providers),
                "total_router_models": len(router_model_rows),
            }
        )
    except Exception as exc:
        raise DomainError(
            code="PROVIDER_MODELS_FETCH_FAILED",
            message="Failed to get models",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc
