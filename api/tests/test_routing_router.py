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

    def test_inventory_error_uses_fallback_provider_list(self, client):
        with patch(
            "api.routing_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ), patch(
            "api.routing_router.dispatcher.list_providers",
            return_value=[
                {"id": "openai", "hidden": False, "configured": True},
                {"id": "mock", "hidden": True, "configured": True},
            ],
        ):
            response = client.get("/routing/providers")
            assert response.status_code == 200
            assert response.json() == ["openai"]


class TestGetProviderDetails:
    def test_returns_inventory(self, client):
        fake_inventory = [
            {
                "id": "openai",
                "configured": False,
                "health": "unknown",
                "is_selectable": False,
            },
            {
                "id": "aliyun",
                "configured": False,
                "health": "unknown",
                "is_selectable": False,
            },
        ]
        with patch(
            "api.routing_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            return_value=fake_inventory,
        ):
            response = client.get("/routing/providers/details")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert any(item.get("id") == "aliyun" for item in data)

    def test_inventory_error_falls_back_to_provider_list(self, client):
        with patch(
            "api.routing_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ), patch(
            "api.routing_router.dispatcher.list_providers",
            return_value=[
                {"id": "openai", "hidden": False},
                {"id": "mock", "hidden": True},
            ],
        ):
            response = client.get("/routing/providers/details")
            assert response.status_code == 200
            assert response.json() == [{"id": "openai", "hidden": False}]

    def test_details_route_not_shadowed_by_capability_route(self, client):
        with patch(
            "api.routing_router.top_providers_for",
            side_effect=RuntimeError("capability route should not be called"),
        ), patch(
            "api.routing_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            return_value=[{"id": "openai", "configured": True}],
        ):
            response = client.get("/routing/providers/details")
            assert response.status_code == 200
            assert response.json() == [{"id": "openai", "configured": True}]

    def test_details_fallback_uses_static_configs_when_provider_list_fails(self, client):
        with patch(
            "api.routing_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("inventory unavailable"),
        ), patch(
            "api.routing_router.dispatcher.list_providers",
            side_effect=RuntimeError("provider list unavailable"),
        ), patch(
            "api.routing_router.dispatcher._configs",
            {
                "openai": {
                    "name": "OpenAI",
                    "models": ["gpt-4o-mini"],
                    "capabilities": ["chat"],
                    "priority_tier": 10,
                    "tier": "cloud",
                },
                "mock": {
                    "name": "Mock",
                    "hidden": True,
                },
            },
        ), patch(
            "api.routing_router.dispatcher.is_configured",
            side_effect=lambda provider_id: provider_id == "openai",
        ):
            response = client.get("/routing/providers/details")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "openai"
            assert data[0]["configured"] is True


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
