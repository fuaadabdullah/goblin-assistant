"""Tests for ProviderDispatcher test mode injection and behavior."""

import asyncio

import pytest

from api.providers.base import ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.routing.router import registry

from .conftest import StubProvider


@pytest.mark.asyncio
async def test_dispatcher_test_mode_injects_failures_and_restores(monkeypatch):
    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")

    async def ok_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(ok=True, text="ok", provider="openai", model=model or "gpt-4o-mini")

    monkeypatch.setattr(provider, "invoke", ok_invoke)

    async with dispatcher.test_mode(
        {"openai": {"fail_after_calls": 0, "error_category": "timeout", "latency_ms": 1}}
    ):
        first = await dispatcher.dispatch(
            pid="openai",
            model="gpt-4o-mini",
            payload={"messages": [{"role": "user", "content": "hi"}]},
        )
        second = await dispatcher.dispatch(
            pid="openai",
            model="gpt-4o-mini",
            payload={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert provider.circuit_state == "soft_open"
    provider.reset_circuit()
    restored = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert first["ok"] is False
    assert first["error_category"] == "timeout"
    assert second["ok"] is False
    assert restored["ok"] is True


@pytest.mark.asyncio
async def test_dispatcher_test_mode_falls_back_to_next_provider(monkeypatch):
    dispatcher = ProviderDispatcher(
        configs={
            "openai": {
                "endpoint": "http://localhost/openai",
                "default_model": "gpt-4o-mini",
            },
            "groq": {
                "endpoint": "http://localhost/groq",
                "default_model": "llama-3.1-8b-instant",
            },
        },
        class_map={"openai": StubProvider, "groq": StubProvider},
    )
    monkeypatch.setattr(dispatcher, "_hybrid_order", lambda: ["openai", "groq"])

    openai = dispatcher.get_provider("openai")
    groq = dispatcher.get_provider("groq")

    async def failing_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        return ProviderResult(
            ok=False,
            provider="openai",
            model=model or "gpt-4o-mini",
            error="simulated timeout",
            error_category="timeout",
        )

    async def success_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        return ProviderResult(
            ok=True,
            text="groq ok",
            provider="groq",
            model=model or "llama-3.1-8b-instant",
        )

    monkeypatch.setattr(openai, "invoke", failing_invoke)
    monkeypatch.setattr(groq, "invoke", success_invoke)

    async with dispatcher.test_mode(
        {"openai": {"fail_after_calls": 0, "error_category": "timeout", "latency_ms": 1}}
    ):
        result = await dispatcher.dispatch(
            pid=None,
            model=None,
            payload={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert result["ok"] is True
    assert result["provider"] == "groq"
    assert result["result"]["text"] == "groq ok"


@pytest.mark.asyncio
async def test_dispatcher_test_mode_injects_stream_failure(monkeypatch):
    dispatcher = ProviderDispatcher(
        configs={
            "openai": {
                "endpoint": "http://localhost/openai",
                "default_model": "gpt-4o-mini",
            }
        },
        class_map={"openai": StubProvider},
    )

    provider = dispatcher.get_provider("openai")

    async def stream_should_not_run(*args, **kwargs):
        _ = args, kwargs
        raise AssertionError("stream path should be short-circuited by test mode")

    monkeypatch.setattr(provider, "stream", stream_should_not_run)

    async with dispatcher.test_mode(
        {"openai": {"fail_after_calls": 0, "error_category": "timeout", "latency_ms": 5}}
    ):
        result = await dispatcher.dispatch(
            pid="openai",
            model="gpt-4o-mini",
            payload={"messages": [{"role": "user", "content": "hi"}]},
            stream=True,
        )

    assert result["ok"] is False
    assert result["error_category"] == "timeout"
    assert result["error"] == "test-mode timeout failure"


@pytest.mark.asyncio
async def test_dispatcher_test_mode_can_override_health_check(monkeypatch):
    dispatcher = ProviderDispatcher(
        configs={
            "openai": {
                "endpoint": "http://localhost/openai",
                "default_model": "gpt-4o-mini",
            }
        },
        class_map={"openai": StubProvider},
    )
    provider = dispatcher.get_provider("openai")

    async def health_should_not_run():
        raise AssertionError("health_check should be injected by test mode")

    monkeypatch.setattr(provider, "health_check", health_should_not_run)

    async with dispatcher.test_mode(
        {
            "openai": {
                "health_check": {
                    "healthy": False,
                    "latency_ms": 7,
                    "error": "simulated outage",
                    "billing_issue": True,
                }
            }
        }
    ):
        health = await dispatcher.check_provider("openai")

    assert health["healthy"] is False
    assert health["health"] == "billing_issue"
    assert health["billing_issue"] is True
    assert health["latency_ms"] == 7.0


@pytest.mark.asyncio
async def test_dispatcher_test_mode_preserves_rate_limit_category(monkeypatch):
    dispatcher = ProviderDispatcher(
        configs={
            "openai": {
                "endpoint": "http://localhost/openai",
                "default_model": "gpt-4o-mini",
            }
        },
        class_map={"openai": StubProvider},
    )

    async with dispatcher.test_mode(
        {
            "openai": {
                "fail_after_calls": 0,
                "error_category": "rate-limit",
                "error": "exceeded your current quota",
            }
        }
    ):
        result = await dispatcher.dispatch(
            pid="openai",
            model="gpt-4o-mini",
            payload={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert result["ok"] is False
    assert result["error_category"] == "rate-limit"
    assert dispatcher.get_provider("openai").circuit_state == "hard_open"


@pytest.mark.asyncio
async def test_dispatcher_test_mode_latency_reaches_metrics(monkeypatch):
    dispatcher = ProviderDispatcher(
        configs={
            "openai": {
                "endpoint": "http://localhost/openai",
                "default_model": "gpt-4o-mini",
            }
        },
        class_map={"openai": StubProvider},
    )
    provider = dispatcher.get_provider("openai")
    captured: dict[str, float] = {}
    original_record_success = registry.record_success

    def capture_record_success(provider_id, *, latency_ms, cost_usd, **kwargs):
        captured["latency_ms"] = float(latency_ms)
        return original_record_success(
            provider_id, latency_ms=latency_ms, cost_usd=cost_usd, **kwargs
        )

    monkeypatch.setattr(registry, "record_success", capture_record_success)

    async def success_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        return ProviderResult(
            ok=True,
            text="ok",
            provider="openai",
            model=model or "gpt-4o-mini",
            latency_ms=1.0,
        )

    monkeypatch.setattr(provider, "invoke", success_invoke)

    async with dispatcher.test_mode({"openai": {"fail_after_calls": 10, "latency_ms": 40}}):
        result = await dispatcher.dispatch(
            pid="openai",
            model="gpt-4o-mini",
            payload={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert result["ok"] is True
    assert captured["latency_ms"] >= 40.0
