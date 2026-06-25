from fastapi import FastAPI
from fastapi.routing import APIRoute

from api.ops_router import router as ops_router


def _ops_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ops_router, prefix="/api/v1")
    return app


def test_reset_route_registered_once() -> None:
    app = _ops_app()
    matches = [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == "/api/v1/ops/circuit-breakers/{provider_name}/reset"
        and "POST" in route.methods
    ]
    assert len(matches) == 1


def test_expected_ops_routes_present() -> None:
    app = _ops_app()
    paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1/ops/")
    }

    assert "/api/v1/ops/health/summary" in paths
    assert "/api/v1/ops/providers/status" in paths
    assert "/api/v1/ops/performance/snapshot" in paths
    assert "/api/v1/ops/queues/snapshot" in paths
    assert "/api/v1/ops/circuit-breakers" in paths
    assert "/api/v1/ops/circuit-breakers/{provider_name}/reset" in paths
    assert "/api/v1/ops/metrics/history" in paths
    assert "/api/v1/ops/aggregated" in paths
    assert "/api/v1/ops/health/trends" in paths
    assert "/api/v1/ops/streaming/analysis" in paths
    assert "/api/v1/ops/security/status" in paths
    assert "/api/v1/ops/audit/log" in paths
    assert "/api/v1/ops/recommendations" in paths
