from __future__ import annotations

import warnings

from fastapi import APIRouter, FastAPI

from tooling.generators.route_manifest import build_manifest


def test_build_manifest_tracks_canonical_versioned_routes() -> None:
    app = FastAPI()

    versioned_settings_router = APIRouter(prefix="/api/v1")

    @versioned_settings_router.get("/settings", operation_id="read_settings_v1")
    async def read_settings_v1() -> dict[str, str]:
        return {"ok": "yes"}

    app.include_router(versioned_settings_router)

    internal_router = APIRouter()

    @internal_router.get("/internal", include_in_schema=False, operation_id="read_internal")
    async def read_internal() -> dict[str, str]:
        return {"ok": "no"}

    app.include_router(internal_router)

    manifest = build_manifest(app)
    routes = {route["path"]: route for route in manifest["routes"]}

    assert manifest["route_count"] == 2
    assert manifest["public_route_count"] == 1
    assert manifest["versioned_route_count"] == 1
    assert manifest["alias_route_count"] == 0
    assert routes["/api/v1/settings"]["logical_path"] == "/settings"
    assert routes["/api/v1/settings"]["compatibility_aliases"] == []
    assert routes["/api/v1/settings"]["deprecated"] is False
    assert routes["/api/v1/settings"]["canonical_path"] == "/api/v1/settings"
    assert routes["/api/v1/settings"]["replacement_path"] is None
    assert routes["/internal"]["include_in_schema"] is False


def test_build_manifest_ignores_hidden_operational_aliases() -> None:
    app = FastAPI()

    @app.get("/api/v1/health", operation_id="health_check")
    async def health_check() -> dict[str, str]:
        return {"ok": "yes"}

    @app.get("/health", include_in_schema=False, operation_id="versionless_health_check")
    async def versionless_health_check() -> dict[str, str]:
        return {"ok": "yes"}

    manifest = build_manifest(app)
    routes = {route["path"]: route for route in manifest["routes"]}

    assert manifest["route_count"] == 1
    assert manifest["public_route_count"] == 1
    assert manifest["alias_route_count"] == 0
    assert "/health" not in routes
    assert routes["/api/v1/health"]["compatibility_aliases"] == []
    assert routes["/api/v1/health"]["canonical_path"] == "/api/v1/health"


def test_build_manifest_orders_methods_and_paths_deterministically() -> None:
    app = FastAPI()

    ordered_router = APIRouter()

    @ordered_router.api_route("/zeta", methods=["POST", "GET"], operation_id="zeta_route")
    async def zeta_route() -> dict[str, str]:
        return {"ok": "yes"}

    @ordered_router.api_route("/alpha", methods=["PUT", "DELETE"], operation_id="alpha_route")
    async def alpha_route() -> dict[str, str]:
        return {"ok": "yes"}

    app.include_router(ordered_router)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Duplicate Operation ID*")
        manifest = build_manifest(app)
    routes = manifest["routes"]

    assert [route["path"] for route in routes] == ["/alpha", "/alpha", "/zeta", "/zeta"]
    assert [route["method"] for route in routes] == ["DELETE", "PUT", "GET", "POST"]
