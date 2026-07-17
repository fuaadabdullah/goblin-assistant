from __future__ import annotations

import json
from pathlib import Path

from fastapi.routing import APIRoute

from api.main import app


def test_api_v1_aliases_cover_key_routes():
    paths = {route.path for route in app.routes}
    expected = {
        "/api/v1/auth/login",
        "/api/v1/search/query",
        "/api/v1/account/profile",
        "/api/v1/settings/",
        "/api/v1/support/message",
        "/api/v1/chat/conversations",
        "/api/v1/providers/models",
    }
    missing = sorted(expected - paths)
    assert not missing, f"Missing /api/v1 aliases: {missing}"
    assert "/settings/" not in paths, "Legacy /settings/ route should stay retired"


def test_checked_in_route_manifest_stays_aligned_with_key_contracts():
    root = Path(__file__).resolve().parents[5]
    manifest = json.loads((root / "packages/sdk/openapi/routes.json").read_text())
    openapi = json.loads((root / "packages/sdk/openapi/openapi.json").read_text())

    manifest_routes = {
        (entry["method"], entry["path"]): entry
        for entry in manifest["routes"]
        if entry["include_in_schema"]
    }
    live_routes: set[tuple[str, str]] = set()
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods or set():
                if method not in {"HEAD", "OPTIONS"}:
                    live_routes.add((method, route.path))

    critical_routes = {
        ("GET", "/api/v1/health", "/health"),
        ("GET", "/api/v1/providers/models", "/providers/models"),
        ("PUT", "/api/v1/account/preferences", "/account/preferences"),
        ("POST", "/api/v1/support/message", "/support/message"),
        ("GET", "/api/v1/settings/", "/api/v1/settings/"),
    }

    missing_manifest = sorted(
        (method, path)
        for method, path, _ in critical_routes
        if (method, path) not in manifest_routes
    )
    missing_live = sorted(
        (method, path) for method, path, _ in critical_routes if (method, path) not in live_routes
    )
    missing_openapi = sorted(
        logical_path
        for _, _, logical_path in critical_routes
        if logical_path not in openapi["paths"]
    )

    assert not missing_manifest, (
        f"Missing critical routes from checked-in manifest: {missing_manifest}"
    )
    assert not missing_live, f"Missing critical routes from live app: {missing_live}"
    assert not missing_openapi, (
        f"Missing critical routes from checked-in OpenAPI: {missing_openapi}"
    )

    settings_v1 = manifest_routes[("GET", "/api/v1/settings/")]
    providers_v1 = manifest_routes[("GET", "/api/v1/providers/models")]
    routing_legacy = manifest_routes[("GET", "/api/v1/routing/providers")]
    assert settings_v1["compatibility_aliases"] == []
    assert settings_v1["deprecated"] is False
    assert settings_v1["replacement_path"] is None
    assert settings_v1["canonical_path"] == "/api/v1/settings/"
    assert providers_v1["deprecated"] is False
    assert providers_v1["canonical_path"] == "/api/v1/providers/models"
    assert routing_legacy["deprecated"] is True
    assert routing_legacy["replacement_path"] == "/api/v1/providers/models"
    assert openapi["paths"]["/routing/providers"]["get"]["deprecated"] is True
