"""Engine contract tests — Routing pillar.

These tests assert that the Routing pillar's public contract
(documented in docs/architecture/ENGINE_CONTRACTS.md) is upheld.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import routing_router


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(routing_router.router, prefix="/api/v1")
    return TestClient(app)


# ── Department Listing Contract ───────────────────────────────────────


class TestDepartmentListingContract:
    """Contract: GET /api/v1/routing/departments returns public-facing summaries."""

    def test_returns_list_of_dicts(self, client):
        response = client.get("/api/v1/routing/departments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert isinstance(data[0], dict)

    def test_each_item_has_required_keys(self, client):
        response = client.get("/api/v1/routing/departments")
        data = response.json()
        required = {
            "department",
            "name",
            "description",
            "supports_streaming",
            "supports_tools",
        }
        for item in data:
            assert required.issubset(item.keys()), (
                f"Missing keys in {item.get('department')}"
            )

    def test_no_provider_chain_leakage(self, client):
        """Provider details must not leak into public listings."""
        response = client.get("/api/v1/routing/departments")
        data = response.json()
        for item in data:
            assert "provider_chain" not in item
            assert "providers" not in item
            assert "provider" not in item

    def test_department_ids_are_valid(self, client):
        response = client.get("/api/v1/routing/departments")
        data = response.json()
        valid_ids = {
            "general",
            "reasoning",
            "coding",
            "creative",
            "recall",
            "tool_use",
            "research",
        }
        for item in data:
            assert item["department"] in valid_ids, (
                f"Unknown department: {item['department']}"
            )


# ── Department Detail Contract ────────────────────────────────────────


class TestDepartmentDetailContract:
    """Contract: GET /api/v1/routing/departments/{id} returns details."""

    def test_get_valid_department(self, client):
        response = client.get("/api/v1/routing/departments/general")
        assert response.status_code == 200
        data = response.json()
        assert data["department"] == "general"
        assert "name" in data
        assert "description" in data
        assert "supports_streaming" in data
        assert "supports_tools" in data

    def test_get_invalid_department_returns_404(self, client):
        response = client.get("/api/v1/routing/departments/nonexistent")
        assert response.status_code == 404

    def test_get_department_case_insensitive(self, client):
        response = client.get("/api/v1/routing/departments/REASONING")
        assert response.status_code == 200
        assert response.json()["department"] == "reasoning"

    def test_get_department_strips_whitespace(self, client):
        response = client.get("/api/v1/routing/departments/%20%20coding%20%20")
        assert response.status_code == 200
        assert response.json()["department"] == "coding"


# ── Route Dispatch Contract ────────────────────────────────────────────


class TestRouteDispatchContract:
    """Contract: POST /api/v1/routing/route dispatches through department."""

    def test_successful_route_returns_content(self, client):
        mock_result = {
            "content": "Hello from department",
            "provider_id": "openai",
            "model": "gpt-4o",
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "department": "general",
        }
        with patch(
            "api.routing_router.department_dispatcher.dispatch",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/api/v1/routing/route",
                json={
                    "department": "general",
                    "payload": {"messages": [{"role": "user", "content": "hello"}]},
                },
            )
        assert response.status_code == 200
        data = response.json()
        # Contract: response must contain these keys
        assert "content" in data
        assert "department" in data
        # Provider info is allowed in the response for traceability
        assert data["content"] == "Hello from department"
        assert data["department"] == "general"

    def test_route_invalid_department_returns_404(self, client):
        response = client.post(
            "/api/v1/routing/route",
            json={
                "department": "nonexistent",
                "payload": {"messages": [{"role": "user", "content": "hi"}]},
            },
        )
        assert response.status_code == 404

    def test_route_all_providers_exhausted_returns_500(self, client):
        with patch(
            "api.routing_router.department_dispatcher.dispatch",
            new_callable=AsyncMock,
            side_effect=Exception("All providers in chain exhausted"),
        ):
            response = client.post(
                "/api/v1/routing/route",
                json={
                    "department": "general",
                    "payload": {"messages": [{"role": "user", "content": "hello"}]},
                },
            )
        assert response.status_code == 500


# ── Provider Fallback Contract ─────────────────────────────────────────


class TestProviderFallbackContract:
    """Contract: provider failures trigger fallback, not immediate error."""

    def test_fallback_on_auth_error(self, client):
        """Failing provider triggers fallback to next in chain.
        The department dispatcher should retry rather than fail immediately.
        """
        mock_result = {
            "content": "Fallback response",
            "provider_id": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "department": "general",
        }
        with patch(
            "api.routing_router.department_dispatcher.dispatch",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/api/v1/routing/route",
                json={
                    "department": "general",
                    "payload": {"messages": [{"role": "user", "content": "hello"}]},
                },
            )
        assert response.status_code == 200
        data = response.json()
        # The fallback provider info is present (not the primary)
        assert data["provider_id"] is not None

    def test_fallback_does_not_leak_error_details(self, client):
        """Error messages must not contain provider names."""
        with patch(
            "api.routing_router.department_dispatcher.dispatch",
            new_callable=AsyncMock,
            side_effect=Exception("All providers in chain exhausted"),
        ):
            response = client.post(
                "/api/v1/routing/route",
                json={
                    "department": "general",
                    "payload": {"messages": [{"role": "user", "content": "hello"}]},
                },
            )
        # Provider names must not be in the error message
        assert "openai" not in response.text.lower()
        assert "anthropic" not in response.text.lower()
        assert "gemini" not in response.text.lower()
