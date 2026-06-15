from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.admin_routes import provider_state
from api.admin_routes import router as admin_router
from api.ops.security import OpsSecurityConfig, ops_security


class _ProviderStub:
    def __init__(self, *, circuit: Dict[str, Any], can_route: bool = True) -> None:
        self._circuit = dict(circuit)
        self._can_route = can_route

    def circuit_status(self) -> Dict[str, Any]:
        return dict(self._circuit)

    def should_attempt(self, *, canary: bool = False) -> bool:
        _ = canary
        return self._can_route


class _DispatcherStub:
    def __init__(self) -> None:
        self._providers = {
            "local_stub": _ProviderStub(
                circuit={
                    "state": "closed",
                    "failure_count": 0,
                    "transient_failure_count": 0,
                    "last_error": None,
                    "open_until": 0.0,
                    "cooldown_remaining_seconds": 0.0,
                    "probe_available": True,
                    "probe_taken": False,
                    "available": True,
                }
            ),
            "openai": _ProviderStub(
                circuit={
                    "state": "closed",
                    "failure_count": 0,
                    "transient_failure_count": 0,
                    "last_error": None,
                    "open_until": 0.0,
                    "cooldown_remaining_seconds": 0.0,
                    "probe_available": True,
                    "probe_taken": False,
                    "available": True,
                }
            ),
        }

    def debug_info(self) -> Dict[str, Any]:
        return {
            "routing_table": [
                {
                    "provider_id": "local_stub",
                    "name": "Local Stub",
                    "priority_tier": 1,
                    "tier": "self_hosted",
                    "local_routing": True,
                    "configured": True,
                    "instantiated": True,
                    "circuit_breaker": self._providers["local_stub"].circuit_status(),
                    "hidden": False,
                    "capabilities": ["chat"],
                    "default_model": "stub-model",
                    "warmup": {"state": "warming", "latency_ms": 122.0},
                },
                {
                    "provider_id": "openai",
                    "name": "OpenAI",
                    "priority_tier": 2,
                    "tier": "cloud",
                    "local_routing": False,
                    "configured": True,
                    "instantiated": True,
                    "circuit_breaker": self._providers["openai"].circuit_status(),
                    "hidden": False,
                    "capabilities": ["chat"],
                    "default_model": "gpt-4o-mini",
                    "warmup": {"state": "warm", "latency_ms": 12.0},
                },
            ],
            "registry_stats": {
                "local_stub": {
                    "ewma_latency_ms": 122.0,
                    "success_rate": 0.9,
                    "total_cost_usd": 0.0,
                    "last_used": 1.0,
                },
                "openai": {
                    "ewma_latency_ms": 12.0,
                    "success_rate": 1.0,
                    "total_cost_usd": 0.12,
                    "last_used": 2.0,
                },
            },
            "registry_metrics": {
                "providers": {
                    "local_stub": {"ewma_latency_ms": 122.0},
                    "openai": {"ewma_latency_ms": 12.0},
                }
            },
            "registry_persisted_snapshot": {},
            "registry_persistence": {},
            "budget_status": {},
            "warmup_states": {
                "local_stub": {"state": "warming", "latency_ms": 122.0},
                "openai": {"state": "warm", "latency_ms": 12.0},
            },
            "routing_min_success_rate": 0.3,
            "circuit_canary_percent": 0.1,
            "model_aliases": {},
            "model_alias_patterns": [],
            "provider_aliases": {},
            "visible_provider_order": ["local_stub", "openai"],
        }

    def get_provider(self, provider_id: str) -> _ProviderStub:
        return self._providers[provider_id]


class _QuotaStub:
    async def snapshot_provider(self, provider_id: str, model: str | None = None) -> Dict[str, Any]:
        if provider_id == "local_stub":
            remaining_requests = 0
            remaining_tokens = 0
        else:
            remaining_requests = 45
            remaining_tokens = 8000

        return {
            "provider_id": provider_id,
            "model": model,
            "canonical_model": model,
            "window_key": "202606050915",
            "provider_scope": {
                "scope": f"provider:{provider_id}:model:{model or ''}",
                "window_key": "202606050915",
                "limits": {
                    "requests_per_minute": 50,
                    "tokens_per_minute": 4000,
                    "concurrency": 4,
                },
                "usage": {
                    "reserved_requests": 50 - remaining_requests
                    if remaining_requests is not None
                    else 0,
                    "reserved_tokens": 4000 - remaining_tokens
                    if remaining_tokens is not None
                    else 0,
                    "committed_requests": 0,
                    "committed_tokens": 0,
                    "active": 0,
                },
                "remaining_requests": remaining_requests,
                "remaining_tokens": remaining_tokens,
                "remaining_concurrency": 4,
                "cooldown_remaining_seconds": 0.0,
            },
            "model_scope": {
                "scope": f"model:{model or ''}",
                "window_key": "202606050915",
                "limits": {
                    "requests_per_minute": 100,
                    "tokens_per_minute": 10000,
                    "concurrency": 8,
                },
                "usage": {
                    "reserved_requests": 0,
                    "reserved_tokens": 0,
                    "committed_requests": 0,
                    "committed_tokens": 0,
                    "active": 0,
                },
                "remaining_requests": 100,
                "remaining_tokens": 10000,
                "remaining_concurrency": 8,
                "cooldown_remaining_seconds": 0.0,
            },
        }


@pytest.fixture
def provider_state_env(monkeypatch):
    monkeypatch.setattr(OpsSecurityConfig, "ENVIRONMENT", "development")
    monkeypatch.setattr(OpsSecurityConfig, "REQUIRE_AUTH", False)
    ops_security.rate_limit_cache.clear()


@pytest.mark.asyncio
async def test_build_provider_state_includes_warmup_circuit_and_quota(
    monkeypatch, provider_state_env
):
    _ = provider_state_env
    monkeypatch.setattr(provider_state, "dispatcher", _DispatcherStub())
    monkeypatch.setattr(provider_state, "quota_service", _QuotaStub())

    state = await provider_state._build_provider_state()

    assert state["summary"]["total_providers"] == 2
    assert state["providers"]["local_stub"]["skip_reason"] == "warmup_warming"
    assert state["providers"]["local_stub"]["can_route"] is False
    assert state["providers"]["openai"]["can_route"] is True
    assert state["providers"]["openai"]["quota"]["provider_scope"]["remaining_requests"] == 45
    assert state["providers"]["local_stub"]["circuit_breaker"]["cooldown_remaining_seconds"] == 0.0


def test_provider_state_route_is_mounted_in_root_and_v1(monkeypatch, provider_state_env):
    _ = provider_state_env
    monkeypatch.setattr(provider_state, "dispatcher", _DispatcherStub())
    monkeypatch.setattr(provider_state, "quota_service", _QuotaStub())

    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/v1")

    client = TestClient(app)

    root_response = client.get("/api/v1/admin/providers/state")
    versioned_response = client.get("/v1/api/v1/admin/providers/state")

    assert root_response.status_code == 200
    assert versioned_response.status_code == 200
    assert root_response.json()["summary"]["total_providers"] == 2
    assert versioned_response.json()["providers"]["local_stub"]["skip_reason"] == "warmup_warming"
