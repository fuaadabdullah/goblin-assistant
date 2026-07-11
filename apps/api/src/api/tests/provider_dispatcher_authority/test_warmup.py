"""Tests for ProviderDispatcher warmup and self-hosted provider behavior."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from api.providers.dispatcher import ProviderDispatcher

from .conftest import StubProvider, WarmupProvider


@pytest.mark.asyncio
async def test_dispatcher_prewarm_updates_warmup_state(monkeypatch):
    monkeypatch.setenv("ENABLE_SELF_HOSTED_PREWARM", "true")
    monkeypatch.setenv("LOCAL_STUB_ENDPOINT", "http://localhost")
    dispatcher = ProviderDispatcher(
        configs={
            "local_stub": {
                "tier": "self_hosted",
                "endpoint_env": "LOCAL_STUB_ENDPOINT",
                "default_model": "stub-model",
            }
        },
        class_map={"local_stub": WarmupProvider},
    )

    dispatcher.start_background_tasks()
    await asyncio.sleep(0.05)

    warmup = dispatcher._warmup_state_for("local_stub")
    assert warmup["state"] == "warm"
    assert warmup["latency_ms"] == 10.0


@pytest.mark.asyncio
async def test_dispatcher_allows_self_hosted_providers_while_warming(monkeypatch):
    monkeypatch.setenv("LOCAL_STUB_ENDPOINT", "http://localhost")
    dispatcher = ProviderDispatcher(
        configs={
            "local_stub": {
                "tier": "self_hosted",
                "endpoint_env": "LOCAL_STUB_ENDPOINT",
                "default_model": "stub-model",
                "capabilities": ["chat"],
            }
        },
        class_map={"local_stub": StubProvider},
    )
    dispatcher._warmup_states["local_stub"] = {"state": "warming", "latency_ms": 10.0}

    import api.providers.dispatcher_pkg.execution as execution_module

    reservation = type(
        "QuotaReservationStub",
        (),
        {"estimated_input_tokens": 1, "estimated_output_tokens": 1},
    )()
    monkeypatch.setattr(
        execution_module.quota_service,
        "reserve",
        AsyncMock(return_value=reservation),
    )
    monkeypatch.setattr(execution_module.quota_service, "commit", AsyncMock())
    monkeypatch.setattr(execution_module.quota_service, "release", AsyncMock())
    monkeypatch.setattr(execution_module.quota_service, "mark_rate_limited", AsyncMock())

    result = await dispatcher.dispatch(
        pid="local_stub",
        model=None,
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "local_stub"
    assert dispatcher._warmup_state_for("local_stub")["state"] == "warm"


@pytest.mark.asyncio
async def test_dispatcher_allows_self_hosted_providers_when_warmup_failed(monkeypatch):
    monkeypatch.setenv("LOCAL_STUB_ENDPOINT", "http://localhost")
    dispatcher = ProviderDispatcher(
        configs={
            "local_stub": {
                "tier": "self_hosted",
                "endpoint_env": "LOCAL_STUB_ENDPOINT",
                "default_model": "stub-model",
                "capabilities": ["chat"],
            }
        },
        class_map={"local_stub": StubProvider},
    )
    dispatcher._warmup_states["local_stub"] = {"state": "failed", "latency_ms": 10.0}

    import api.providers.dispatcher_pkg.execution as execution_module

    reservation = AsyncMock(
        return_value={
            "ok": True,
            "provider_id": "local_stub",
            "model": "stub-model",
            "reservation_id": "res-1",
        }
    )

    monkeypatch.setattr(execution_module.quota_service, "reserve", reservation)
    monkeypatch.setattr(execution_module.quota_service, "commit", AsyncMock())
    monkeypatch.setattr(execution_module.quota_service, "release", AsyncMock())
    monkeypatch.setattr(execution_module.quota_service, "mark_rate_limited", AsyncMock())

    assert dispatcher._warmup_state_for("local_stub")["state"] == "failed"

    result = await dispatcher.dispatch(
        pid="local_stub",
        model=None,
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "local_stub"
    assert reservation.await_count == 1
    assert dispatcher._warmup_state_for("local_stub")["state"] == "warm"


@pytest.mark.asyncio
async def test_self_hosted_provider_is_not_selectable_without_env(monkeypatch):
    monkeypatch.delenv("OLLAMA_GCP_ENDPOINT", raising=False)
    monkeypatch.delenv("LLAMACPP_GCP_ENDPOINT", raising=False)
    monkeypatch.delenv("COLAB_WORKER_ENDPOINT", raising=False)
    monkeypatch.delenv("COLAB_WORKER_API_KEY", raising=False)
    monkeypatch.delenv("VERTEX_AI_PROJECT", raising=False)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    dispatcher = ProviderDispatcher(
        configs={"gcp_vm": {"tier": "private", "selectable_requires_env": True}},
    )
    status = await dispatcher.check_provider("gcp_vm")

    assert status["configured"] is False
    assert status["is_selectable"] is False
    assert status["health_reason"] == "Provider not configured"
