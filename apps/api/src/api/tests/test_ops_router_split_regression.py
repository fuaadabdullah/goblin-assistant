from fastapi import FastAPI
from fastapi.routing import APIRoute

from api.ops_router import router as ops_router


def _ops_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ops_router)
    return app


def test_reset_route_registered_once() -> None:
    app = _ops_app()
    matches = [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == "/ops/circuit-breakers/{provider_name}/reset"
        and "POST" in route.methods
    ]
    assert len(matches) == 1


def test_expected_ops_routes_present() -> None:
    app = _ops_app()
    paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/ops/")
    }

    assert "/ops/health/summary" in paths
    assert "/ops/providers/status" in paths
    assert "/ops/performance/snapshot" in paths
    assert "/ops/queues/snapshot" in paths
    assert "/ops/circuit-breakers" in paths
    assert "/ops/circuit-breakers/{provider_name}/reset" in paths
    assert "/ops/metrics/history" in paths
    assert "/ops/aggregated" in paths
    assert "/ops/health/trends" in paths
    assert "/ops/streaming/analysis" in paths
    assert "/ops/security/status" in paths
    assert "/ops/audit/log" in paths
    assert "/ops/recommendations" in paths
