import asyncio

import pytest

from api.providers.base import BaseProvider, ProviderHealth, ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.routing.router import hybrid_router, registry


class _StubProvider(BaseProvider):
    async def invoke(self, messages=None, model=None, **kwargs):
        return ProviderResult(ok=True, provider=self.provider_id, model=model or "stub")

    async def stream(self, messages=None, model=None, **kwargs):
        if False:
            yield {}

    async def health_check(self):
        return ProviderHealth(provider_id=self.provider_id, healthy=True)


def test_provider_result_to_dict_uses_compat_shape():
    result = ProviderResult(
        ok=True,
        text="hello",
        raw={"id": "raw-1"},
        provider="openai",
        model="gpt-4o-mini",
        usage={"total_tokens": 42},
        cost_usd=0.123,
        latency_ms=12.5,
    )

    assert result.to_dict() == {
        "ok": True,
        "result": {
            "text": "hello",
            "raw": {"id": "raw-1"},
            "usage": {"total_tokens": 42},
            "cost_usd": 0.123,
        },
        "provider": "openai",
        "model": "gpt-4o-mini",
        "latency_ms": 12.5,
        "error": None,
    }


def test_base_provider_circuit_breaker_opens_after_three_failures():
    provider = _StubProvider("stub", {"default_model": "stub-model"})

    provider.record_failure("first")
    provider.record_failure("second")
    assert provider.is_available() is True

    provider.record_failure("third")
    assert provider.is_available() is False

    provider.record_success()
    assert provider.is_available() is True


def test_dispatcher_resolves_provider_aliases():
    dispatcher = ProviderDispatcher()

    assert dispatcher.get_provider("google").provider_id == "gemini"
    assert dispatcher.get_provider("azure-openai").provider_id == "azure_openai"
    assert dispatcher.get_provider("vertex").provider_id == "vertex_ai"


@pytest.mark.asyncio
async def test_dispatcher_routes_model_alias_to_matching_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    dispatcher = ProviderDispatcher()
    anthropic = dispatcher.get_provider("anthropic")

    async def fake_invoke(messages=None, model=None, **kwargs):
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="hi",
            provider="anthropic",
            model=model or "",
            usage={"input_tokens": 1, "output_tokens": 1},
            cost_usd=0.0,
            latency_ms=1.0,
        )

    monkeypatch.setattr(anthropic, "invoke", fake_invoke)

    result = await dispatcher.dispatch(
        pid=None,
        model="claude-haiku",
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "anthropic"
    assert result["model"] == "claude-3-5-haiku-latest"


@pytest.mark.asyncio
async def test_self_hosted_provider_is_not_selectable_without_env(monkeypatch):
    monkeypatch.delenv("OLLAMA_GCP_ENDPOINT", raising=False)

    dispatcher = ProviderDispatcher()
    status = await dispatcher.check_provider("ollama_gcp")

    assert status["configured"] is False
    assert status["is_selectable"] is False
    assert status["health_reason"] == "Provider not configured"


def test_candidate_order_auto_uses_hybrid_router(monkeypatch):
    dispatcher = ProviderDispatcher()

    monkeypatch.setattr(dispatcher, "_priority_order", lambda: ["p1", "p2"])
    monkeypatch.setattr(dispatcher, "_provider_costs", lambda _pid: (0.1, 0.2))

    called = {"count": 0}

    def fake_rank(candidates, provider_costs):
        called["count"] += 1
        assert candidates == ["p1", "p2"]
        assert set(provider_costs.keys()) == {"p1", "p2"}
        return ["p2", "p1"]

    monkeypatch.setattr(hybrid_router, "rank", fake_rank)

    assert dispatcher._candidate_order(None) == ["p2", "p1"]
    assert called["count"] == 1


@pytest.mark.asyncio
async def test_dispatch_success_records_provider_and_registry(monkeypatch):
    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")

    async def fake_invoke(messages=None, model=None, **kwargs):
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

    # Force circuit open first; success path must close it via provider.record_success().
    provider.record_failure("f1")
    provider.record_failure("f2")
    provider.record_failure("f3")
    assert provider.is_available() is False

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
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="openai",
            model=model or "gpt-4o-mini",
            error="upstream rejected request",
            latency_ms=2.0,
        )

    monkeypatch.setattr(provider, "invoke", fake_invoke)

    before_failure_count = provider._failure_count
    before_registry_failures = registry.get("openai").failure_count

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert result["ok"] is False
    assert "upstream rejected request" in result["error"]
    assert provider._failure_count >= before_failure_count + 1
    assert registry.get("openai").failure_count == before_registry_failures + 1


@pytest.mark.asyncio
async def test_dispatch_registry_gate_falls_back_to_configured_candidates(monkeypatch):
    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")

    # Ensure this candidate fails the registry success-rate gate.
    stats = registry.get("openai")
    stats.success_count = 0
    stats.failure_count = 10

    dispatcher._routing_min_success_rate = 0.9
    monkeypatch.setattr(dispatcher, "_candidate_order", lambda _pid: ["openai"])
    monkeypatch.setattr(dispatcher, "is_configured", lambda _pid: True)
    monkeypatch.setattr(provider, "is_available", lambda: True)

    async def fake_invoke(messages=None, model=None, **kwargs):
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

    # Even with gate filtering out `available`, dispatcher should still use configured fallback.
    assert result["ok"] is True
    assert result["provider"] == "openai"
