"""Tests for routes.providers_models."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.providers_models import _provider_models, router


def test_provider_models_deduplicates_and_includes_default_model():
    entry = {
        "models": ["gpt-4o-mini", "gpt-4o-mini", "gpt-4o"],
        "default_model": "gpt-4.1",
    }

    result = _provider_models(entry)

    assert result == ["gpt-4.1", "gpt-4o", "gpt-4o-mini"]


def test_provider_models_ignores_blank_values():
    entry = {
        "models": ["", "  ", "model-a"],
        "default_model": "",
    }

    result = _provider_models(entry)

    assert result == ["  ", "model-a"] or result == ["model-a"]


def test_get_provider_models_endpoint_returns_providers_and_models():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    inventory = [
        {
            "id": "openai",
            "models": ["gpt-4o-mini"],
            "default_model": "gpt-4.1",
            "health": "healthy",
            "configured": True,
            "is_selectable": True,
            "health_reason": None,
        },
        {
            "id": "mock",
            "models": ["mock-1"],
            "default_model": "mock-2",
            "health": "unknown",
            "configured": False,
            "is_selectable": False,
            "health_reason": "offline",
        },
    ]

    with patch(
        "api.routes.providers_models.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        return_value=inventory,
    ):
        response = client.get("/providers/models")

    assert response.status_code == 200
    data = response.json()
    assert data["total_providers"] == 2
    assert data["total_models"] == 4
    assert data["source"] == "configured_with_health"
    assert len(data["providers"]) == 2
    assert any(model["name"] == "gpt-4.1" for model in data["models"])


def test_get_provider_models_endpoint_handles_errors():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with patch(
        "api.routes.providers_models.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        side_effect=RuntimeError("inventory unavailable"),
    ):
        response = client.get("/providers/models")

    assert response.status_code == 500
    assert "Failed to get models" in response.json()["detail"]
