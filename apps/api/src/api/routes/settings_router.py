from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import get_current_user
from api.core.contracts import SuccessEnvelope
from api.core.errors import DomainError
from api.providers.dispatcher import dispatcher
from api.routing.router import top_providers_for
from api.storage.database import get_db
from api.storage.saas_service import SaaSSettingsService

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)],
)


class ProviderSettings(BaseModel):
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    models: List[str] = []
    enabled: bool = True
    priority: Optional[int] = None
    weight: Optional[float] = None


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


class SettingsUpdatedResponse(BaseModel):
    message: str
    settings: dict
    scope: Optional[str] = None


class ProviderConnectionResponse(BaseModel):
    status: str
    message: str
    connected: bool


def _provider_models(entry: dict) -> List[str]:
    models = list(entry.get("models", []))
    default_model = str(entry.get("default_model", "")).strip()
    if default_model and default_model not in models:
        models.append(default_model)
    return sorted({model for model in models if model})


@router.get("/", response_model=SuccessEnvelope[SettingsResponse])
async def get_settings(db: AsyncSession = Depends(get_db)):
    try:
        inventory = await dispatcher.get_provider_inventory(include_hidden=False)
        service = SaaSSettingsService(db)
        overlays = {row.provider_name: row for row in await service.list_provider_settings()}
        providers = [
            ProviderSettings(
                name=entry["id"],
                api_key="stored"
                if overlays.get(entry["id"]) and overlays[entry["id"]].api_key_encrypted
                else entry.get("api_key_env"),
                base_url=(overlays.get(entry["id"]).base_url if overlays.get(entry["id"]) else None)
                or entry.get("endpoint")
                or None,
                endpoint=(overlays.get(entry["id"]).endpoint if overlays.get(entry["id"]) else None)
                or entry.get("endpoint")
                or None,
                models=(
                    list(overlays.get(entry["id"]).models)
                    if overlays.get(entry["id"]) and overlays[entry["id"]].models
                    else _provider_models(entry)
                ),
                enabled=bool(
                    overlays.get(entry["id"]).enabled
                    if overlays.get(entry["id"])
                    else entry.get("configured")
                ),
                priority=(
                    overlays.get(entry["id"]).priority if overlays.get(entry["id"]) else None
                ),
                weight=(overlays.get(entry["id"]).weight if overlays.get(entry["id"]) else None),
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
        saved_default_provider = await service.get_global_setting("default_provider")
        if isinstance(saved_default_provider, str) and saved_default_provider.strip():
            default_provider = saved_default_provider
        default_model = None
        if default_provider:
            default_model = (
                str(dispatcher.get_provider_config(default_provider).get("default_model", ""))
                or dispatcher.get_provider(default_provider).default_model
            )
        saved_default_model = await service.get_global_setting("default_model")
        if isinstance(saved_default_model, str) and saved_default_model.strip():
            default_model = saved_default_model

        return SuccessEnvelope(
            data=SettingsResponse(
                providers=providers,
                models=models,
                default_provider=default_provider,
                default_model=default_model,
            )
        )
    except Exception as exc:
        raise DomainError(
            code="SETTINGS_FETCH_FAILED",
            message="Failed to get settings",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc


@router.post("/test-connection", response_model=SuccessEnvelope[ProviderConnectionResponse])
async def test_provider_connection(provider_name: str):
    try:
        result = await dispatcher.check_provider(provider_name)
        return SuccessEnvelope(
            data=ProviderConnectionResponse(
                status="success" if result.get("healthy") else "warning",
                message=(
                    f"Connection test successful for {provider_name}"
                    if result.get("healthy")
                    else result.get("health_reason")
                    or f"Connection test failed for {provider_name}"
                ),
                connected=bool(result.get("healthy")),
            )
        )
    except Exception as exc:
        raise DomainError(
            code="PROVIDER_CONNECTION_TEST_FAILED",
            message="Connection test failed",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc


@router.put(
    "/providers/{provider_name}",
    response_model=SuccessEnvelope[SettingsUpdatedResponse],
)
async def update_provider_settings(
    provider_name: str,
    settings: ProviderSettings,
    db: AsyncSession = Depends(get_db),
):
    if not settings.name:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Provider name is required",
            status_code=400,
        )
    service = SaaSSettingsService(db)
    row = await service.upsert_provider_settings(
        provider_name,
        {
            "endpoint": settings.endpoint or settings.base_url,
            "base_url": settings.base_url,
            "enabled": settings.enabled,
            "priority": settings.priority,
            "weight": settings.weight,
            "models": settings.models,
            "api_key": settings.api_key,
        },
    )
    return SuccessEnvelope(
        data=SettingsUpdatedResponse(
            message=f"Settings updated for provider: {provider_name}",
            settings={
                "provider_name": row.provider_name,
                "endpoint": row.endpoint,
                "base_url": row.base_url,
                "enabled": row.enabled,
                "priority": row.priority,
                "weight": row.weight,
                "models": row.models,
            },
            scope="provider",
        )
    )


@router.put("/models/{model_name}", response_model=SuccessEnvelope[SettingsUpdatedResponse])
async def update_model_settings(
    model_name: str,
    settings: ModelSettings,
    db: AsyncSession = Depends(get_db),
):
    if not settings.name or not settings.provider or not settings.model_id:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Model name, provider, and model_id are required",
            status_code=400,
        )
    service = SaaSSettingsService(db)
    await service.set_global_setting(f"model:{model_name}", settings.model_dump())
    return SuccessEnvelope(
        data=SettingsUpdatedResponse(
            message=f"Settings updated for model: {model_name}",
            settings=settings.model_dump(),
            scope="model",
        )
    )


@router.patch("/{key}", response_model=SuccessEnvelope[Dict[str, Any]])
async def update_global_setting(
    key: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    service = SaaSSettingsService(db)
    stored = await service.set_global_setting(key, payload.get("value"))
    return SuccessEnvelope(data=stored)
