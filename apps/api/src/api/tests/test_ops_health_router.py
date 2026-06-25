from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.ops_health import ops_health_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(ops_health_router, prefix="/ops")
    return TestClient(app)


def test_ops_health_summary_preserves_exception_message(monkeypatch):
    async def fake_summary(**kwargs):
        del kwargs
        raise RuntimeError("summary unavailable")

    monkeypatch.setattr("api.ops_health.build_ops_health_summary", fake_summary)

    response = _client().get("/ops/health/summary")

    assert response.status_code == 500
    assert response.json()["detail"] == "Health summary failed: summary unavailable"


def test_ops_provider_status_preserves_exception_message(monkeypatch):
    async def fake_status(**kwargs):
        del kwargs
        raise RuntimeError("provider status unavailable")

    monkeypatch.setattr("api.ops_health.build_provider_status_payload", fake_status)

    response = _client().get("/ops/providers/status")

    assert response.status_code == 500
    assert response.json()["detail"] == "Provider status failed: provider status unavailable"
