"""Tests for the /routing FastAPI router endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# GET /routing/providers
# ---------------------------------------------------------------------------

class TestGetProviders:
    def test_returns_list(self, client):
        response = client.get("/routing/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_returns_only_configured_providers(self, client):
        """Configured providers should appear in the list."""
        response = client.get("/routing/providers")
        data = response.json()
        # At minimum, mock should be excluded (hidden) but any configured real provider present
        assert isinstance(data, list)
        assert "mock" not in data

    def test_inventory_error_returns_empty(self, client):
        with patch(
            "api.routing_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            response = client.get("/routing/providers")
            assert response.status_code == 200
            assert response.json() == []


# ---------------------------------------------------------------------------
# GET /routing/providers/{capability}
# ---------------------------------------------------------------------------

class TestGetProvidersByCapability:
    def test_chat_capability(self, client):
        with patch(
            "api.routing_router.top_providers_for",
            return_value=["openai", "anthropic"],
        ):
            response = client.get("/routing/providers/chat")
            assert response.status_code == 200
            assert response.json() == ["openai", "anthropic"]

    def test_unknown_capability_returns_empty(self, client):
        with patch(
            "api.routing_router.top_providers_for",
            return_value=[],
        ):
            response = client.get("/routing/providers/telekinesis")
            assert response.status_code == 200
            assert response.json() == []

    def test_exception_returns_empty(self, client):
        with patch(
            "api.routing_router.top_providers_for",
            side_effect=RuntimeError("oops"),
        ):
            response = client.get("/routing/providers/chat")
            assert response.status_code == 200
            assert response.json() == []


# ---------------------------------------------------------------------------
# POST /routing/route
# ---------------------------------------------------------------------------

class TestRouteRequest:
    def test_successful_route(self, client):
        fake_result = {
            "ok": True,
            "text": "routed-response",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "selected_provider": "openai",
        }
        with patch(
            "api.routing_router.route_task",
            new_callable=AsyncMock,
            return_value=fake_result,
        ):
            response = client.post(
                "/routing/route",
                json={
                    "task_type": "chat",
                    "payload": {"messages": [{"role": "user", "content": "hi"}]},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["selected_provider"] == "openai"

    def test_route_with_preferences(self, client):
        with patch(
            "api.routing_router.route_task",
            new_callable=AsyncMock,
            return_value={"ok": True, "provider": "llamacpp_gcp"},
        ) as mock_route:
            response = client.post(
                "/routing/route",
                json={
                    "task_type": "chat",
                    "payload": {"messages": [{"role": "user", "content": "hi"}]},
                    "prefer_local": True,
                    "prefer_cost": False,
                    "max_retries": 3,
                },
            )
            assert response.status_code == 200
            mock_route.assert_awaited_once()
            call_kwargs = mock_route.call_args.kwargs
            assert call_kwargs["prefer_local"] is True
            assert call_kwargs["max_retries"] == 3

    def test_route_failure_returns_500(self, client):
        with patch(
            "api.routing_router.route_task",
            new_callable=AsyncMock,
            side_effect=RuntimeError("no providers"),
        ):
            response = client.post(
                "/routing/route",
                json={
                    "task_type": "chat",
                    "payload": {},
                },
            )
            assert response.status_code == 500
            assert "Routing failed" in response.json()["detail"]

    def test_route_no_providers(self, client):
        with patch(
            "api.routing_router.route_task",
            new_callable=AsyncMock,
            return_value={"ok": False, "error": "no providers available", "providers_tried": []},
        ):
            response = client.post(
                "/routing/route",
                json={
                    "task_type": "chat",
                    "payload": {},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False
