"""Tests for the /settings FastAPI router endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# GET /settings/
# ---------------------------------------------------------------------------

class TestGetSettings:
    def test_returns_settings_shape(self, client):
        fake_inventory = [
            {
                "id": "openai",
                "api_key_env": "OPENAI_API_KEY",
                "endpoint": "https://api.openai.com",
                "models": ["gpt-4o", "gpt-4o-mini"],
                "default_model": "gpt-4o-mini",
                "configured": True,
            },
            {
                "id": "anthropic",
                "api_key_env": "ANTHROPIC_API_KEY",
                "endpoint": "https://api.anthropic.com",
                "models": ["claude-sonnet-4-20250514"],
                "default_model": "claude-sonnet-4-20250514",
                "configured": False,
            },
        ]
        with patch(
            "api.settings_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            return_value=fake_inventory,
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
            response = client.get("/settings/")
            assert response.status_code == 200
            data = response.json()

            assert "providers" in data
            assert "models" in data
            assert "default_provider" in data
            assert "default_model" in data

            provider_names = [p["name"] for p in data["providers"]]
            assert "openai" in provider_names
            assert "anthropic" in provider_names

            # Configured flag
            openai_entry = next(p for p in data["providers"] if p["name"] == "openai")
            assert openai_entry["enabled"] is True

            anthropic_entry = next(p for p in data["providers"] if p["name"] == "anthropic")
            assert anthropic_entry["enabled"] is False

    def test_models_are_deduplicated(self, client):
        """default_model should be merged into models without duplicates."""
        fake_inventory = [
            {
                "id": "test_provider",
                "models": ["model-a", "model-b"],
                "default_model": "model-a",  # already in models list
                "configured": True,
            },
        ]
        with patch(
            "api.settings_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            return_value=fake_inventory,
        ), patch(
            "api.settings_router.top_providers_for",
            return_value=[],
        ):
            response = client.get("/settings/")
            assert response.status_code == 200
            data = response.json()
            provider = data["providers"][0]
            assert sorted(provider["models"]) == ["model-a", "model-b"]

    def test_settings_error_returns_500(self, client):
        with patch(
            "api.settings_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            response = client.get("/settings/")
            assert response.status_code == 500
            assert "Failed to get settings" in response.json()["detail"]


# ---------------------------------------------------------------------------
# PUT /settings/providers/{provider_name}
# ---------------------------------------------------------------------------

class TestUpdateProviderSettings:
    def test_update_returns_success(self, client):
        response = client.put(
            "/settings/providers/openai",
            json={
                "name": "openai",
                "api_key": "sk-test",
                "base_url": "https://api.openai.com",
                "models": ["gpt-4o"],
                "enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "openai" in data["message"]

    def test_update_empty_name_returns_400(self, client):
        response = client.put(
            "/settings/providers/openai",
            json={"name": "", "models": [], "enabled": True},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# PUT /settings/models/{model_name}
# ---------------------------------------------------------------------------

class TestUpdateModelSettings:
    def test_update_model_returns_success(self, client):
        response = client.put(
            "/settings/models/gpt-4o",
            json={
                "name": "gpt-4o",
                "provider": "openai",
                "model_id": "gpt-4o",
                "temperature": 0.5,
                "enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_update_model_missing_fields_returns_400(self, client):
        response = client.put(
            "/settings/models/gpt-4o",
            json={
                "name": "",
                "provider": "",
                "model_id": "",
                "enabled": True,
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /settings/test-connection
# ---------------------------------------------------------------------------

class TestTestConnection:
    def test_successful_connection(self, client):
        with patch(
            "api.settings_router.dispatcher.check_provider",
            new_callable=AsyncMock,
            return_value={"healthy": True},
        ):
            response = client.post(
                "/settings/test-connection",
                params={"provider_name": "openai"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["status"] == "success"

    def test_failed_connection(self, client):
        with patch(
            "api.settings_router.dispatcher.check_provider",
            new_callable=AsyncMock,
            return_value={"healthy": False, "health_reason": "timeout"},
        ):
            response = client.post(
                "/settings/test-connection",
                params={"provider_name": "bad_provider"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert data["status"] == "warning"

    def test_connection_error_returns_500(self, client):
        with patch(
            "api.settings_router.dispatcher.check_provider",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network error"),
        ):
            response = client.post(
                "/settings/test-connection",
                params={"provider_name": "openai"},
            )
            assert response.status_code == 500
