"""Tests for the debug suggestion router."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.debug import router


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


def _client() -> TestClient:
    return TestClient(_build_app(), raise_server_exceptions=False)


def test_debug_router_model_routing_failure() -> None:
    with patch("api.routes.debug.model_router") as mock_router:
        mock_router.choose_model.side_effect = RuntimeError("routing boom")

        response = _client().post(
            "/api/v1/debug/suggest",
            json={"task": "quick_fix", "context": {}},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Model routing failed: routing boom"


def test_debug_router_model_call_failure() -> None:
    with patch("api.routes.debug.model_router") as mock_router:
        route = MagicMock()
        route.model_name = "fallback"
        mock_router.choose_model.return_value = route
        mock_router.call_model = AsyncMock(side_effect=Exception("call boom"))

        response = _client().post(
            "/api/v1/debug/suggest",
            json={"task": "quick_fix", "context": {}},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "Model call failed: call boom"
