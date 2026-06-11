"""Tests for the /routing FastAPI router endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import routing_router as _routing_router_module


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(_routing_router_module.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /routing/providers  (deprecated — still must not 500)
# ---------------------------------------------------------------------------


class TestGetProviders:
    def test_returns_list(self, client):
        response = client.get("/routing/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_returns_only_configured_providers(self, client):
        response = client.get("/routing/providers")
        data = response.json()
        assert isinstance(data, list)
        assert "mock" not in data

    def test_inventory_error_falls_back_to_department_ids(self, client):
        with (
            patch(
                "api.routing_router.dispatcher.get_provider_inventory",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "api.routing_router.DEPARTMENT_REGISTRY.list_ids",
                return_value=["general", "coding"],
            ),
        ):
            response = client.get("/routing/providers")
            assert response.status_code == 200
            assert response.json() == ["general", "coding"]

    def test_empty_inventory_falls_back_to_department_ids(self, client):
        with (
            patch(
                "api.routing_router.dispatcher.get_provider_inventory",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "api.routing_router.DEPARTMENT_REGISTRY.list_ids",
                return_value=["general", "reasoning"],
            ),
        ):
            response = client.get("/routing/providers")
            assert response.status_code == 200
            assert response.json() == ["general", "reasoning"]


# ---------------------------------------------------------------------------
# GET /routing/departments  +  GET /routing/departments/{id}
# ---------------------------------------------------------------------------


class TestGetDepartments:
    def test_list_departments_returns_list(self, client):
        response = client.get("/routing/departments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_departments_has_department_key(self, client):
        fake = [{"department": "general", "name": "General", "description": "d"}]
        with patch(
            "api.routing_router.DEPARTMENT_REGISTRY.list_public",
            return_value=fake,
        ):
            response = client.get("/routing/departments")
            assert response.status_code == 200
            data = response.json()
            assert all("department" in item for item in data)

    def test_get_department_by_id_returns_details(self, client):
        policy = MagicMock()
        policy.department_id.value = "reasoning"
        policy.display_name = "Reasoning"
        policy.description = "Logic and math"
        policy.supports_streaming = True
        policy.supports_tools = True
        with patch(
            "api.routing_router.DEPARTMENT_REGISTRY.get_by_id_str",
            return_value=policy,
        ):
            response = client.get("/routing/departments/reasoning")
            assert response.status_code == 200
            data = response.json()
            assert data["department"] == "reasoning"
            assert "name" in data
            assert "description" in data

    def test_get_unknown_department_returns_404(self, client):
        with patch(
            "api.routing_router.DEPARTMENT_REGISTRY.get_by_id_str",
            side_effect=KeyError("nope"),
        ):
            response = client.get("/routing/departments/nonexistent")
            assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /routing/providers/{capability}  (deprecated — dict-lookup behaviour)
# ---------------------------------------------------------------------------


class TestGetProvidersByCapability:
    def test_chat_capability_returns_known_departments(self, client):
        response = client.get("/routing/providers/chat")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "general" in data

    def test_coding_capability_returns_coding_department(self, client):
        response = client.get("/routing/providers/coding")
        assert response.status_code == 200
        data = response.json()
        assert "coding" in data

    def test_unknown_capability_falls_back_to_all_departments(self, client):
        with patch(
            "api.routing_router.DEPARTMENT_REGISTRY.list_ids",
            return_value=["general", "coding", "reasoning"],
        ):
            response = client.get("/routing/providers/telekinesis")
            assert response.status_code == 200
            data = response.json()
            assert data == ["general", "coding", "reasoning"]

    def test_capability_lookup_is_case_insensitive(self, client):
        response_lower = client.get("/routing/providers/chat")
        response_upper = client.get("/routing/providers/CHAT")
        assert response_lower.status_code == 200
        assert response_upper.status_code == 200
        assert response_lower.json() == response_upper.json()


# ---------------------------------------------------------------------------
# POST /routing/route
# ---------------------------------------------------------------------------


class TestRouteRequest:
    def test_successful_route(self, client):
        fake_result = {
            "ok": True,
            "text": "routed-response",
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
        }
        with patch(
            "api.routing_router.department_dispatcher.dispatch",
            new_callable=AsyncMock,
            return_value=fake_result,
        ):
            response = client.post(
                "/routing/route",
                json={
                    "department": "general",
                    "payload": {"messages": [{"role": "user", "content": "hi"}]},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["department"] == "general"

    def test_route_strips_internal_fields(self, client):
        fake_result = {
            "ok": True,
            "_department": "general",
            "_department_reason": "default",
            "text": "hello",
        }
        with patch(
            "api.routing_router.department_dispatcher.dispatch",
            new_callable=AsyncMock,
            return_value=fake_result,
        ):
            response = client.post(
                "/routing/route",
                json={"department": "general", "payload": {}},
            )
            data = response.json()
            assert "_department" not in data
            assert "_department_reason" not in data

    def test_unknown_department_returns_404(self, client):
        with patch(
            "api.routing_router.DEPARTMENT_REGISTRY.get",
            side_effect=KeyError("nope"),
        ):
            response = client.post(
                "/routing/route",
                json={"department": "imaginary", "payload": {}},
            )
            assert response.status_code == 404

    def test_dispatch_failure_returns_500(self, client):
        with patch(
            "api.routing_router.department_dispatcher.dispatch",
            new_callable=AsyncMock,
            side_effect=RuntimeError("provider unavailable"),
        ):
            response = client.post(
                "/routing/route",
                json={"department": "general", "payload": {}},
            )
            assert response.status_code == 500
            body = response.json()
            assert "detail" in body
            assert "Department routing failed" in body["detail"]

    def test_stream_defaults_to_false(self, client):
        captured = {}

        def capture_dispatch(**kwargs):
            captured["stream"] = kwargs.get("stream")
            return {"ok": True}

        with patch(
            "api.routing_router.department_dispatcher.dispatch",
            new_callable=AsyncMock,
            side_effect=capture_dispatch,
        ):
            client.post(
                "/routing/route",
                json={"department": "general", "payload": {}},
            )
        assert captured.get("stream") is False
