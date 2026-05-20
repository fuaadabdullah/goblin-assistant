from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _jwt_secret_for_app(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "test-local-llm-key")


def _make_client():
    import api.main as main

    return TestClient(main.app)


def test_provider_models_deduplicates_and_sorts():
    from api.settings_router import _provider_models

    assert _provider_models(
        {"models": ["b", "a", "a"], "default_model": "c"}
    ) == ["a", "b", "c"]


def test_provider_models_ignores_blank_values():
    from api.settings_router import _provider_models

    assert _provider_models(
        {"models": ["", "alpha"], "default_model": " "}
    ) == ["alpha"]


def test_get_settings_success():
    inventory = [
        {
            "id": "openai",
            "api_key_env": "OPENAI_API_KEY",
            "endpoint": "https://api.openai.com",
            "models": ["gpt-4o-mini"],
            "default_model": "gpt-4o-mini",
            "configured": True,
        }
    ]

    with patch(
        "api.settings_router.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        return_value=inventory,
    ), patch(
        "api.settings_router.top_providers_for",
        return_value=["openai"],
    ), patch(
        "api.settings_router.dispatcher.get_provider_config",
        return_value={"default_model": "gpt-4o-mini"},
    ), patch(
        "api.settings_router.dispatcher.get_provider",
        return_value=MagicMock(default_model="gpt-4o-mini"),
    ):
        with _make_client() as client:
            response = client.get("/settings/")

    assert response.status_code == 200
    body = response.json()
    assert body["default_provider"] == "openai"
    assert body["default_model"] == "gpt-4o-mini"
    assert body["providers"][0]["enabled"] is True


def test_get_settings_failure():
    with patch(
        "api.settings_router.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        with _make_client() as client:
            response = client.get("/settings/")

    assert response.status_code == 500
    assert "Failed to get settings" in response.json()["detail"]


def test_update_provider_and_model_settings():
    with _make_client() as client:
        provider_resp = client.put(
            "/settings/providers/openai",
            json={
                "name": "openai",
                "api_key": "sk-test",
                "base_url": "https://api.openai.com",
                "models": ["gpt-4o-mini"],
                "enabled": True,
            },
        )
        assert provider_resp.status_code == 200
        assert provider_resp.json()["status"] == "success"

        model_resp = client.put(
            "/settings/models/gpt-4o-mini",
            json={
                "name": "gpt-4o-mini",
                "provider": "openai",
                "model_id": "gpt-4o-mini",
                "temperature": 0.5,
                "enabled": True,
            },
        )
        assert model_resp.status_code == 200
        assert model_resp.json()["status"] == "success"
