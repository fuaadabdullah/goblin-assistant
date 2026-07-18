from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.auth.router import User, get_current_user
from api.core.contracts import ErrorEnvelope
from api.core.error_types import ErrorType
from api.core.errors import DomainError
from api.settings_router import router


@pytest.fixture(autouse=True)
def _jwt_secret_for_app(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "test-local-llm-key")


def _make_client():
    app = FastAPI()

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorEnvelope(
                error={
                    "code": exc.code,
                    "type": ErrorType.BUSINESS_LOGIC,
                    "message": exc.message,
                    "details": exc.details,
                }
            ).model_dump(exclude_none=True),
        )

    app.include_router(router, prefix="/api/v1")
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: User(
        id="user-123",
        email="user@example.com",
    )
    return TestClient(app)


def test_provider_models_deduplicates_and_sorts():
    from api.settings_router import _provider_models

    assert _provider_models({"models": ["b", "a", "a"], "default_model": "c"}) == [
        "a",
        "b",
        "c",
    ]


def test_provider_models_ignores_blank_values():
    from api.settings_router import _provider_models

    assert _provider_models({"models": ["", "alpha"], "default_model": " "}) == ["alpha"]


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

    with (
        patch(
            "api.settings_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            return_value=inventory,
        ),
        patch(
            "api.settings_router.top_providers_for",
            return_value=["openai"],
        ),
        patch(
            "api.settings_router.dispatcher.get_provider_config",
            return_value={"default_model": "gpt-4o-mini"},
        ),
        patch(
            "api.settings_router.dispatcher.get_provider",
            return_value=MagicMock(default_model="gpt-4o-mini"),
        ),
        patch(
            "api.settings_router.SaaSSettingsService.list_provider_settings",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "api.settings_router.SaaSSettingsService.get_global_setting",
            new_callable=AsyncMock,
            return_value=None,
        ),
        _make_client() as client,
    ):
        response = client.get("/settings/")
        legacy_response = client.get("/api/v1/settings/")

    assert response.status_code == 200
    assert legacy_response.status_code == 200
    body = response.json()["data"]
    assert legacy_response.json()["data"] == body
    assert body["default_provider"] == "openai"
    assert body["default_model"] == "gpt-4o-mini"
    assert body["providers"][0]["enabled"] is True


def test_get_settings_failure():
    with (
        patch(
            "api.settings_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ),
        patch(
            "api.settings_router.SaaSSettingsService.list_provider_settings",
            new_callable=AsyncMock,
            return_value=[],
        ),
        _make_client() as client,
    ):
        response = client.get("/settings/")
        legacy_response = client.get("/api/v1/settings/")

    assert response.status_code == 500
    assert legacy_response.status_code == 500
    assert response.json()["error"]["code"] == "SETTINGS_FETCH_FAILED"
    assert legacy_response.json()["error"]["code"] == "SETTINGS_FETCH_FAILED"


def test_update_provider_and_model_settings():
    with (
        _make_client() as client,
        patch(
            "api.settings_router.SaaSSettingsService.upsert_provider_settings",
            new_callable=AsyncMock,
            return_value=MagicMock(
                provider_name="openai",
                endpoint="https://api.openai.com",
                base_url="https://api.openai.com",
                enabled=True,
                priority=None,
                weight=None,
                models=["gpt-4o-mini"],
            ),
        ),
        patch(
            "api.settings_router.SaaSSettingsService.set_global_setting",
            new_callable=AsyncMock,
            return_value={"key": "model:gpt-4o-mini", "value": {"name": "gpt-4o-mini"}},
        ),
    ):
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
        assert provider_resp.json()["data"]["message"] == "Settings updated for provider: openai"

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
        assert model_resp.json()["data"]["message"] == "Settings updated for model: gpt-4o-mini"


def test_patch_global_setting_accepts_valid_payload():
    current_user = User(id="user-1", email="user-1@example.com")

    app = FastAPI()

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorEnvelope(
                error={
                    "code": exc.code,
                    "type": ErrorType.BUSINESS_LOGIC,
                    "message": exc.message,
                    "details": exc.details,
                }
            ).model_dump(exclude_none=True),
        )

    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    with patch(
        "api.routes.settings_router.SaaSSettingsService.set_global_setting",
        new_callable=AsyncMock,
        return_value={"key": "theme", "value": {"mode": "dark"}},
    ):
        response = client.patch(
            "/api/v1/settings/theme",
            json={"value": {"mode": "dark"}},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["key"] == "theme"
    assert response.json()["data"]["value"] == {"mode": "dark"}
