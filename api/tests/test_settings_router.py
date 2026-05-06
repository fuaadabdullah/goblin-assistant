"""Tests for api.settings_router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.settings_router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_get_settings_maps_inventory_to_response():
    client = _client()

    fake_provider = MagicMock()
    fake_provider.default_model = "gpt-4o-mini"

    with patch(
        "api.settings_router.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        return_value=[
            {
                "id": "openai",
                "configured": True,
                "api_key_env": "OPENAI_API_KEY",
                "endpoint": "https://example.com",
                "models": ["gpt-4o-mini"],
                "default_model": "gpt-4o-mini",
            }
        ],
    ), patch(
        "api.settings_router.top_providers_for",
        return_value=["openai"],
    ), patch(
        "api.settings_router.dispatcher.get_provider_config",
        return_value={"default_model": "gpt-4o-mini"},
    ), patch(
        "api.settings_router.dispatcher.get_provider",
        return_value=fake_provider,
    ):
        response = client.get("/settings/")

    assert response.status_code == 200
    data = response.json()
    assert data["default_provider"] == "openai"
    assert data["default_model"] == "gpt-4o-mini"
    assert data["providers"][0]["name"] == "openai"
    assert data["models"][0]["provider"] == "openai"


def test_get_settings_returns_500_on_inventory_failure():
    client = _client()

    with patch(
        "api.settings_router.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        response = client.get("/settings/")

    assert response.status_code == 500
    assert "Failed to get settings" in response.json()["detail"]


def test_update_provider_settings_rejects_blank_name():
    client = _client()

    response = client.put(
        "/settings/providers/openai",
        json={"name": "", "enabled": True},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Provider name is required"


def test_update_model_settings_accepts_valid_payload():
    client = _client()

    response = client.put(
        "/settings/models/gpt-4o-mini",
        json={
            "name": "gpt-4o-mini",
            "provider": "openai",
            "model_id": "gpt-4o-mini",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["settings"]["provider"] == "openai"


def test_test_provider_connection_reports_health_states():
    client = _client()

    with patch(
        "api.settings_router.dispatcher.check_provider",
        new_callable=AsyncMock,
        return_value={"healthy": True},
    ):
        healthy = client.post(
            "/settings/test-connection",
            params={"provider_name": "openai"},
        )

    with patch(
        "api.settings_router.dispatcher.check_provider",
        new_callable=AsyncMock,
        return_value={"healthy": False, "health_reason": "timeout"},
    ):
        unhealthy = client.post(
            "/settings/test-connection",
            params={"provider_name": "openai"},
        )

    assert healthy.status_code == 200
    assert healthy.json()["status"] == "success"

    assert unhealthy.status_code == 200
    assert unhealthy.json()["status"] == "warning"
    assert unhealthy.json()["message"] == "timeout"
