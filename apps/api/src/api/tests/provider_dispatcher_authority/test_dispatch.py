"""Tests for ProviderDispatcher dispatch, failover, and registry recording."""

import asyncio
import importlib

import pytest

from api.providers.base import ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.routing.router import registry

dispatcher_module = importlib.import_module("api.providers.dispatcher")


@pytest.mark.asyncio
async def test_dispatch_success_records_provider_and_registry(monkeypatch):
    base_module = importlib.import_module("api.providers.base")

    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")

    async def fake_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="ok",
            provider="openai",
            model=model or "gpt-4o-mini",
            usage={"input_tokens": 1, "output_tokens": 1},
            cost_usd=0.01,
            latency_ms=5.0,
        )

    monkeypatch.setattr(provider, "invoke", fake_invoke)

    # Success path must close the circuit via provider.record_success().
    now = 1_000.0
    monkeypatch.setattr(base_module.time, "time", lambda: now)
    provider.record_failure("timeout 1", category="timeout")
    provider.record_failure("timeout 2", category="timeout")
    assert provider.circuit_state == "soft_open"
    monkeypatch.setattr(base_module.time, "time", lambda: now + 31.0)

    stats_before = registry.get("openai")
    before_successes = stats_before.success_count

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "openai"
    assert provider.is_available() is True
    assert registry.get("openai").success_count == before_successes + 1


@pytest.mark.asyncio
async def test_dispatch_soft_failure_records_provider_and_registry(monkeypatch):
    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")

    async def fake_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="openai",
            model=model or "gpt-4o-mini",
            error="upstream rejected request",
            latency_ms=2.0,
        )

    monkeypatch.setattr(provider, "invoke", fake_invoke)

    before_failure_count = getattr(provider, "_failure_count")
    before_registry_failures = registry.get("openai").failure_count

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert result["ok"] is False
    assert "upstream rejected request" in result["error"]
    assert getattr(provider, "_failure_count") >= before_failure_count + 1
    assert registry.get("openai").failure_count == before_registry_failures + 1


@pytest.mark.asyncio
async def test_dispatch_registry_gate_falls_back_to_configured_candidates(monkeypatch):
    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")

    # Ensure this candidate fails the registry success-rate gate.
    stats = registry.get("openai")
    stats.success_count = 0
    stats.failure_count = 10

    setattr(dispatcher, "_routing_min_success_rate", 0.9)
    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["openai"],
    )
    monkeypatch.setattr(dispatcher, "is_configured", lambda _pid: True)
    monkeypatch.setattr(provider, "is_available", lambda: True)

    async def fake_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="ok",
            provider="openai",
            model=model or "gpt-4o-mini",
            latency_ms=3.0,
        )

    monkeypatch.setattr(provider, "invoke", fake_invoke)

    result = await dispatcher.dispatch(
        pid=None,
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    # Dispatcher should still use configured fallback when the gate filters.
    assert result["ok"] is True
    assert result["provider"] == "openai"


@pytest.mark.asyncio
async def test_auto_dispatch_falls_through_to_next_healthy_candidate(monkeypatch):
    dispatcher = ProviderDispatcher()
    openai = dispatcher.get_provider("openai")
    groq = dispatcher.get_provider("groq")

    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["openai", "groq"],
    )
    monkeypatch.setattr(
        dispatcher,
        "_auto_configured_candidates",
        lambda candidates: candidates,
    )
    monkeypatch.setattr(dispatcher, "is_configured", lambda _pid: True)
    monkeypatch.setattr(openai, "is_available", lambda: True)
    monkeypatch.setattr(groq, "is_available", lambda: True)

    async def fail_openai(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="openai",
            model=model or "gpt-4o-mini",
            error="openai unavailable",
            latency_ms=1.0,
        )

    async def succeed_groq(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="fallback answer",
            provider="groq",
            model=model or "llama-3.3-70b-versatile",
            latency_ms=2.0,
        )

    monkeypatch.setattr(openai, "invoke", fail_openai)
    monkeypatch.setattr(groq, "invoke", succeed_groq)

    result = await dispatcher.dispatch(
        pid=None,
        model=None,
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "groq"
    assert result["result"]["text"] == "fallback answer"


@pytest.mark.asyncio
async def test_auto_dispatch_returns_provider_none_when_all_candidates_fail(monkeypatch):
    dispatcher = ProviderDispatcher()
    openai = dispatcher.get_provider("openai")
    groq = dispatcher.get_provider("groq")

    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["openai", "groq"],
    )
    monkeypatch.setattr(
        dispatcher,
        "_auto_configured_candidates",
        lambda candidates: candidates,
    )
    monkeypatch.setattr(dispatcher, "is_configured", lambda _pid: True)
    monkeypatch.setattr(openai, "is_available", lambda: True)
    monkeypatch.setattr(groq, "is_available", lambda: True)

    async def fail_openai(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="openai",
            model=model or "gpt-4o-mini",
            error="openai down",
            error_category="server_error",
            latency_ms=1.0,
        )

    async def fail_groq(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="groq",
            model=model or "llama-3.3-70b-versatile",
            error="groq down",
            error_category="server_error",
            latency_ms=1.5,
        )

    monkeypatch.setattr(openai, "invoke", fail_openai)
    monkeypatch.setattr(groq, "invoke", fail_groq)

    result = await dispatcher.dispatch(
        pid=None,
        model=None,
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is False
    assert result["provider"] == "none"
    assert result["error"] == "groq down"
    assert result["error_category"] == "server-error"


@pytest.mark.asyncio
async def test_auto_dispatch_skips_self_hosted_candidates_by_default(monkeypatch):
    from api.services.provider_health import health_monitor

    dispatcher = ProviderDispatcher()
    gcs = dispatcher.get_provider("gcp_vm")
    groq = dispatcher.get_provider("groq")

    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["gcp_vm", "groq"],
    )
    monkeypatch.setattr(dispatcher, "_allow_self_hosted_auto_routing", lambda: False)
    monkeypatch.setattr(dispatcher, "is_configured", lambda _pid: True)
    monkeypatch.setattr(health_monitor, "is_available", lambda _pid: True)

    async def should_not_run(*args, **kwargs):
        raise AssertionError("self-hosted provider should not be selected")

    async def fake_groq_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="ok",
            provider="groq",
            model=model or "llama-3.3-70b-versatile",
            latency_ms=3.0,
        )

    monkeypatch.setattr(gcs, "invoke", should_not_run)
    monkeypatch.setattr(groq, "invoke", fake_groq_invoke)

    result = await dispatcher.dispatch(
        pid=None,
        model=None,
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "groq"


@pytest.mark.asyncio
async def test_explicit_force_fallback_provider_uses_auto_fallback_chain(monkeypatch):
    dispatcher = ProviderDispatcher()
    gcs = dispatcher.get_provider("gcp_vm")
    groq = dispatcher.get_provider("groq")

    gcs_cfg = dispatcher.__dict__.setdefault("_configs", {}).setdefault(
        "gcp_vm",
        {},
    )
    gcs_cfg["force_fallback"] = True

    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["gcp_vm"],
    )
    monkeypatch.setattr(
        dispatcher,
        "_hybrid_order",
        lambda: ["gcp_vm", "groq"],
    )
    monkeypatch.setattr(
        dispatcher,
        "_auto_configured_candidates",
        lambda candidates: candidates,
    )
    monkeypatch.setattr(
        dispatcher,
        "is_configured",
        lambda _pid: True,
    )

    async def fail_gcs(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="gcp_vm",
            model=model or "qwen2.5:3b",
            error="all gcs backends unavailable",
        )

    async def ok_groq(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="fallback ok",
            provider="groq",
            model=model or "llama-3.3-70b-versatile",
            latency_ms=2.0,
        )

    monkeypatch.setattr(gcs, "invoke", fail_gcs)
    monkeypatch.setattr(groq, "invoke", ok_groq)

    result = await dispatcher.dispatch(
        pid="gcp_vm",
        model="qwen2.5:3b",
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "groq"


@pytest.mark.asyncio
async def test_explicit_provider_without_force_fallback_stays_explicit(monkeypatch):
    dispatcher = ProviderDispatcher()
    openai = dispatcher.get_provider("openai")
    groq = dispatcher.get_provider("groq")

    openai_cfg = dispatcher.__dict__.setdefault("_configs", {}).setdefault(
        "openai",
        {},
    )
    openai_cfg["force_fallback"] = False

    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["openai"],
    )
    monkeypatch.setattr(
        dispatcher,
        "_hybrid_order",
        lambda: ["openai", "groq"],
    )

    async def fail_openai(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="openai",
            model=model or "gpt-4o-mini",
            error="openai failure",
        )

    async def should_not_run(*args, **kwargs):
        raise AssertionError("explicit request should not try fallbacks")

    monkeypatch.setattr(openai, "invoke", fail_openai)
    monkeypatch.setattr(groq, "invoke", should_not_run)

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is False
    assert result["error"] == "openai failure"


@pytest.mark.asyncio
async def test_dispatch_preserves_provider_error_category(monkeypatch):
    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")

    openai_cfg = dispatcher.__dict__.setdefault("_configs", {}).setdefault(
        "openai",
        {},
    )
    _ = openai_cfg

    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["openai"],
    )
    monkeypatch.setattr(dispatcher, "is_configured", lambda _pid: True)

    async def fake_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="openai",
            model=model or "gpt-4o-mini",
            error="backend rejected",
            error_category="rate-limit",
        )

    def fail_classifier(_exc):
        raise AssertionError("classifier should not see error strings")

    monkeypatch.setattr(provider, "invoke", fake_invoke)
    monkeypatch.setattr(dispatcher_module, "classify_provider_error", fail_classifier)

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert result["ok"] is False
    assert result["error"] == "backend rejected"
    assert result["error_category"] == "rate-limit"


@pytest.mark.asyncio
async def test_dispatch_timeout_cancels_inflight_provider_task(monkeypatch):
    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")
    cancelled = asyncio.Event()

    async def hanging_invoke(messages=None, model=None, **kwargs):
        _ = messages, model, kwargs
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.set()

    monkeypatch.setattr(provider, "invoke", hanging_invoke)

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
        timeout_ms=1,
    )

    assert result["ok"] is False
    assert result["error_category"] == "timeout"
    assert cancelled.is_set()
