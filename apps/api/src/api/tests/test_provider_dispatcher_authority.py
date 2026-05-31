import asyncio
import importlib
import re

import pytest

from api.providers.base import BaseProvider, ProviderHealth, ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.routing.router import hybrid_router, registry
from api.services.provider_health import health_monitor

dispatcher_module = importlib.import_module("api.providers.dispatcher")


class _StubProvider(BaseProvider):
    async def invoke(self, messages=None, model=None, **kwargs):
        _ = messages, kwargs
        return ProviderResult(
            ok=True,
            provider=self.provider_id,
            model=model or "stub",
        )

    async def stream(self, messages=None, model=None, **kwargs):
        _ = messages, model, kwargs
        if kwargs.get("never", False):
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


def test_dispatcher_visible_provider_ids_include_together():
    dispatcher = ProviderDispatcher()

    visible_ids = dispatcher.provider_ids(include_hidden=False)

    assert "together" in visible_ids


def test_dispatcher_visible_order_together_before_siliconeflow():
    dispatcher = ProviderDispatcher()

    visible_ids = dispatcher.provider_ids(include_hidden=False)

    assert visible_ids.index("together") < visible_ids.index("siliconeflow")


@pytest.mark.asyncio
async def test_dispatcher_routes_model_alias_to_matching_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    dispatcher = ProviderDispatcher()
    anthropic = dispatcher.get_provider("anthropic")

    async def fake_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
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
async def test_dispatcher_routes_wildcard_model_alias(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        dispatcher_module,
        "_MODEL_ALIAS_PATTERNS",
        [(re.compile(r"^gpt-mini-(.+)$"), "openai", "gpt-4o-mini-{1}")],
    )

    dispatcher = ProviderDispatcher()
    openai = dispatcher.get_provider("openai")

    async def fake_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="ok",
            provider="openai",
            model=model or "",
            latency_ms=1.0,
        )

    monkeypatch.setattr(openai, "invoke", fake_invoke)

    result = await dispatcher.dispatch(
        pid=None,
        model="gpt-mini-coder",
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o-mini-coder"


@pytest.mark.asyncio
async def test_dispatcher_redacts_secrets_in_errors(monkeypatch):
    secret = "sk-secret-value-123456"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    dispatcher = ProviderDispatcher()
    openai = dispatcher.get_provider("openai")

    async def boom(messages=None, model=None, **kwargs):
        _ = messages, model, kwargs
        raise RuntimeError(f"provider failed with key={secret}")

    monkeypatch.setattr(openai, "invoke", boom)

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert result["ok"] is False
    assert "[REDACTED]" in result["error"]
    assert secret not in result["error"]


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

    candidate_order = getattr(dispatcher, "_candidate_order")
    assert candidate_order(None) == ["p2", "p1"]
    assert called["count"] == 1


@pytest.mark.asyncio
async def test_dispatch_success_records_provider_and_registry(monkeypatch):
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
async def test_dispatch_soft_failure_records_provider_and_registry(
    monkeypatch,
):
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
async def test_dispatch_registry_gate_falls_back_to_configured_candidates(
    monkeypatch,
):
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
async def test_auto_dispatch_skips_self_hosted_candidates_by_default(
    monkeypatch,
):
    dispatcher = ProviderDispatcher()
    ollama = dispatcher.get_provider("ollama_gcp")
    groq = dispatcher.get_provider("groq")

    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["ollama_gcp", "groq"],
    )
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

    monkeypatch.setattr(ollama, "invoke", should_not_run)
    monkeypatch.setattr(groq, "invoke", fake_groq_invoke)

    result = await dispatcher.dispatch(
        pid=None,
        model=None,
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "groq"


@pytest.mark.asyncio
async def test_explicit_force_fallback_provider_uses_auto_fallback_chain(
    monkeypatch,
):
    dispatcher = ProviderDispatcher()
    colab = dispatcher.get_provider("colab_worker")
    groq = dispatcher.get_provider("groq")

    colab_cfg = dispatcher.__dict__.setdefault("_configs", {}).setdefault(
        "colab_worker",
        {},
    )
    colab_cfg["force_fallback"] = True

    monkeypatch.setattr(
        dispatcher,
        "_candidate_order",
        lambda _pid: ["colab_worker"],
    )
    monkeypatch.setattr(
        dispatcher,
        "_hybrid_order",
        lambda: ["colab_worker", "groq"],
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

    async def fail_colab(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=False,
            provider="colab_worker",
            model=model or "gemma-3-12b",
            error="colab unavailable",
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

    monkeypatch.setattr(colab, "invoke", fail_colab)
    monkeypatch.setattr(groq, "invoke", ok_groq)

    result = await dispatcher.dispatch(
        pid="colab_worker",
        model="gemma-3-12b",
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "groq"


@pytest.mark.asyncio
async def test_explicit_provider_without_force_fallback_stays_explicit(
    monkeypatch,
):
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
    monkeypatch.setattr(
        dispatcher_module,
        "classify_provider_error",
        fail_classifier,
    )

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert result["ok"] is False
    assert result["error"] == "backend rejected"
    assert result["error_category"] == "rate-limit"


@pytest.mark.asyncio
async def test_health_inventory_times_out_hung_provider(monkeypatch):
    dispatcher = ProviderDispatcher()
    provider = dispatcher.get_provider("openai")

    openai_cfg = dispatcher.__dict__.setdefault("_configs", {}).setdefault(
        "openai",
        {},
    )
    openai_cfg["health_check_timeout_ms"] = 10

    async def slow_health_check():
        await asyncio.sleep(0.05)
        return ProviderHealth(provider_id="openai", healthy=True, latency_ms=5)

    monkeypatch.setattr(dispatcher, "is_configured", lambda _pid: True)
    monkeypatch.setattr(
        dispatcher,
        "list_providers",
        lambda include_hidden=False: [{"id": "openai"}],
    )
    monkeypatch.setattr(provider, "health_check", slow_health_check)

    inventory = await dispatcher.get_provider_inventory()

    assert inventory[0]["healthy"] is False
    assert "timed out" in inventory[0]["health_reason"]


def test_list_providers_uses_cached_snapshot(monkeypatch):
    dispatcher = ProviderDispatcher()
    calls = {"count": 0}

    def fake_builder(include_hidden=False):
        _ = include_hidden
        calls["count"] += 1
        return [{"id": "openai", "hidden": False}]

    monkeypatch.setattr(dispatcher, "_build_provider_list", fake_builder)

    first = dispatcher.list_providers()
    second = dispatcher.list_providers()

    assert calls["count"] == 1
    assert first == second == [{"id": "openai", "hidden": False}]


def test_dispatcher_lazily_instantiates_providers(monkeypatch):
    class CountingProvider(BaseProvider):
        inits = 0

        def __init__(self, provider_id, config=None):
            CountingProvider.inits += 1
            super().__init__(provider_id, config)

        async def invoke(self, messages=None, model=None, **kwargs):
            _ = messages, kwargs
            return ProviderResult(
                ok=True,
                provider=self.provider_id,
                model=model or "stub",
            )

        async def stream(self, messages=None, model=None, **kwargs):
            _ = messages, model, kwargs
            if kwargs.get("never", False):
                yield {}

        async def health_check(self):
            return ProviderHealth(provider_id=self.provider_id, healthy=True)

    provider_class_map = dispatcher_module.__dict__["_PROVIDER_CLASS_MAP"]
    monkeypatch.setitem(provider_class_map, "openai", CountingProvider)
    dispatcher = ProviderDispatcher()

    assert CountingProvider.inits == 0
    dispatcher.get_provider("openai")
    assert CountingProvider.inits == 1


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
