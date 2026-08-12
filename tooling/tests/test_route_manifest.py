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

    @internal_router.get(
        "/internal", include_in_schema=False, operation_id="read_internal"
    )
    async def read_internal() -> dict[str, str]:
        return {"ok": "no"}

    app.include_router(internal_router)

    manifest = build_manifest(app)
    routes = {route["path"]: route for route in manifest["routes"]}

    assert manifest["route_count"] == 1
    assert manifest["public_route_count"] == 1
    assert manifest["versioned_route_count"] == 1
    assert manifest["alias_route_count"] == 0
    assert routes["/api/v1/settings"]["logical_path"] == "/settings"
    assert routes["/api/v1/settings"]["compatibility_aliases"] == []
    assert routes["/api/v1/settings"]["deprecated"] is False
    assert routes["/api/v1/settings"]["canonical_path"] == "/api/v1/settings"
    assert routes["/api/v1/settings"]["replacement_path"] is None
    assert "/internal" not in routes


def test_build_manifest_preserves_openapi_routes_missing_from_live_snapshot() -> None:
    app = FastAPI()

    @app.get("/", operation_id="root")
    async def root() -> dict[str, str]:
        return {"ok": "yes"}

    schema = {
        "paths": {
            "/": {
                "get": {
                    "operationId": "root",
                    "summary": "Root",
                }
            },
            "/api/v1/account/profile": {
                "get": {
                    "operationId": "get_profile",
                    "summary": "Get Profile",
                    "tags": ["account"],
                }
            },
            "/api/v1/routing/providers": {
                "get": {
                    "deprecated": True,
                    "operationId": "get_providers",
                    "summary": "Get Providers",
                    "tags": ["routing"],
                    "x-goblin-replaced-by": "/api/v1/providers/models",
                }
            },
        }
    }

    manifest = build_manifest(app, schema=schema)
    routes = {(route["method"], route["path"]): route for route in manifest["routes"]}

    assert manifest["public_route_count"] == 3
    assert manifest["versioned_route_count"] == 2
    assert routes[("GET", "/api/v1/account/profile")]["include_in_schema"] is True
    assert routes[("GET", "/api/v1/account/profile")]["canonical_path"] == (
        "/api/v1/account/profile"
    )
    assert routes[("GET", "/api/v1/routing/providers")]["deprecated"] is True
    assert routes[("GET", "/api/v1/routing/providers")]["replacement_path"] == (
        "/api/v1/providers/models"
    )


def test_build_manifest_uses_openapi_path_spelling_for_public_path_converters() -> None:
    app = FastAPI()

    @app.get("/api/v1/secrets/{path:path}", operation_id="get_secret")
    async def get_secret(path: str) -> dict[str, str]:
        return {"path": path}

    schema = {
        "paths": {
            "/api/v1/secrets/{path}": {
                "get": {
                    "operationId": "get_secret_api_v1_secrets__path__get",
                    "summary": "Get Secret",
                    "tags": ["secrets"],
                }
            }
        }
    }

    manifest = build_manifest(app, schema=schema)
    routes = {(route["method"], route["path"]): route for route in manifest["routes"]}

    assert manifest["public_route_count"] == 1
    assert manifest["versioned_route_count"] == 1
    assert ("GET", "/api/v1/secrets/{path:path}") not in routes
    assert (
        routes[("GET", "/api/v1/secrets/{path}")]["logical_path"] == "/secrets/{path}"
    )
    assert routes[("GET", "/api/v1/secrets/{path}")]["operation_id"] == (
        "get_secret_api_v1_secrets__path__get"
    )


def test_build_manifest_orders_methods_and_paths_deterministically() -> None:
    app = FastAPI()

    ordered_router = APIRouter()

    @ordered_router.api_route(
        "/zeta", methods=["POST", "GET"], operation_id="zeta_route"
    )
    async def zeta_route() -> dict[str, str]:
        return {"ok": "yes"}

    @ordered_router.api_route(
        "/alpha", methods=["PUT", "DELETE"], operation_id="alpha_route"
    )
    async def alpha_route() -> dict[str, str]:
        return {"ok": "yes"}

    app.include_router(ordered_router)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Duplicate Operation ID*")
        manifest = build_manifest(app)
    routes = manifest["routes"]

    assert [route["path"] for route in routes] == ["/alpha", "/alpha", "/zeta", "/zeta"]
    assert [route["method"] for route in routes] == ["DELETE", "PUT", "GET", "POST"]
