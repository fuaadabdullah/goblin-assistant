"""Provider and model registry backed by the authoritative dispatcher."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List

from api.providers.dispatcher import dispatcher

router = APIRouter(tags=["providers"])


def _provider_models(entry: Dict[str, Any]) -> List[str]:
    models = list(entry.get("models", []))
    default_model = str(entry.get("default_model", "")).strip()
    if default_model and default_model not in models:
        models.append(default_model)
    return sorted({model for model in models if model})


@router.get("/providers/models")
async def get_provider_models() -> Dict[str, Any]:
    try:
        inventory = await dispatcher.get_provider_inventory(include_hidden=False)
        providers: List[Dict[str, Any]] = []
        models: List[Dict[str, Any]] = []

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

        return {
            "models": models,
            "providers": providers,
            "source": "configured_with_health",
            "total_models": len(models),
            "total_providers": len(providers),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get models: {exc}") from exc
