from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from api.providers.dispatcher import dispatcher
from api.routing.router import top_providers_for

router = APIRouter(prefix="/settings", tags=["settings"])


class ProviderSettings(BaseModel):
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: List[str] = []
    enabled: bool = True


class ModelSettings(BaseModel):
    name: str
    provider: str
    model_id: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    enabled: bool = True


class SettingsResponse(BaseModel):
    providers: List[ProviderSettings]
    models: List[ModelSettings]
    default_provider: Optional[str] = None
    default_model: Optional[str] = None


def _provider_models(entry: dict) -> List[str]:
    models = list(entry.get("models", []))
    default_model = str(entry.get("default_model", "")).strip()
    if default_model and default_model not in models:
        models.append(default_model)
    return sorted({model for model in models if model})


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    try:
        inventory = await dispatcher.get_provider_inventory(include_hidden=False)
        providers = [
            ProviderSettings(
                name=entry["id"],
                api_key=entry.get("api_key_env"),
                base_url=entry.get("endpoint") or None,
                models=_provider_models(entry),
                enabled=bool(entry.get("configured")),
            )
            for entry in inventory
        ]

        models: List[ModelSettings] = []
        for entry in inventory:
            provider_id = entry["id"]
            for model_name in _provider_models(entry):
                models.append(
                    ModelSettings(
                        name=model_name,
                        provider=provider_id,
                        model_id=model_name,
                        max_tokens=None,
                        enabled=bool(entry.get("configured")),
                    )
                )

        default_provider = next(iter(top_providers_for("chat", limit=1)), None)
        default_model = None
        if default_provider:
            default_model = str(
                dispatcher.get_provider_config(default_provider).get("default_model", "")
            ) or dispatcher.get_provider(default_provider).default_model

        return SettingsResponse(
            providers=providers,
            models=models,
            default_provider=default_provider,
            default_model=default_model,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {exc}") from exc


@router.put("/providers/{provider_name}")
async def update_provider_settings(provider_name: str, settings: ProviderSettings):
    if not settings.name:
        raise HTTPException(status_code=400, detail="Provider name is required")
    return {
        "status": "success",
        "message": f"Settings updated for provider: {provider_name}",
        "settings": settings.model_dump(),
    }


@router.put("/models/{model_name}")
async def update_model_settings(model_name: str, settings: ModelSettings):
    if not settings.name or not settings.provider or not settings.model_id:
        raise HTTPException(
            status_code=400,
            detail="Model name, provider, and model_id are required",
        )
    return {
        "status": "success",
        "message": f"Settings updated for model: {model_name}",
        "settings": settings.model_dump(),
    }


@router.post("/test-connection")
async def test_provider_connection(provider_name: str):
    try:
        result = await dispatcher.check_provider(provider_name)
        return {
            "status": "success" if result.get("healthy") else "warning",
            "message": (
                f"Connection test successful for {provider_name}"
                if result.get("healthy")
                else result.get("health_reason") or f"Connection test failed for {provider_name}"
            ),
            "connected": bool(result.get("healthy")),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {exc}") from exc
