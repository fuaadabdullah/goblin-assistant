from __future__ import annotations

from api.main import app


def test_api_v1_aliases_cover_key_routes():
    paths = {route.path for route in app.routes}
    expected = {
        "/api/v1/auth/login",
        "/api/v1/search/query",
        "/api/v1/account/profile",
        "/api/v1/support/message",
        "/api/v1/chat/conversations",
        "/api/v1/providers/models",
    }
    missing = sorted(expected - paths)
    assert not missing, f"Missing /api/v1 aliases: {missing}"
