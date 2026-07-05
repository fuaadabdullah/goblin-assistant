from __future__ import annotations

from fastapi import APIRouter, FastAPI

from tooling.generators.route_manifest import build_manifest


def test_build_manifest_tracks_versioned_and_legacy_aliases() -> None:
    app = FastAPI()

    settings_router = APIRouter()

    @settings_router.get("/settings", operation_id="read_settings")
    async def read_settings() -> dict[str, str]:
        return {"ok": "yes"}

    app.include_router(settings_router)

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

    assert manifest["route_count"] == 3
    assert manifest["public_route_count"] == 2
    assert manifest["versioned_route_count"] == 1
    assert manifest["alias_route_count"] == 2
    assert routes["/settings"]["logical_path"] == "/settings"
    assert routes["/settings"]["compatibility_aliases"] == ["/api/v1/settings"]
    assert routes["/api/v1/settings"]["logical_path"] == "/settings"
    assert routes["/api/v1/settings"]["compatibility_aliases"] == ["/settings"]
    assert routes["/internal"]["include_in_schema"] is False
