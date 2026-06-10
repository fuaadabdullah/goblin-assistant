import asyncio
import importlib
import re

import pytest

from api.providers.base import BaseProvider, ProviderHealth, ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.providers.dispatcher_pkg.sanitization import provider_secrets_processor
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


class _WarmupProvider(_StubProvider):
    async def warmup(self):
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            provider=self.provider_id,
            model=self.default_model or "stub",
            latency_ms=10.0,
        )


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


def test_base_provider_circuit_breaker_soft_opens_after_transient_failures():
    provider = _StubProvider("stub", {"default_model": "stub-model"})

    provider.record_failure("timeout one", category="timeout")
    assert provider.circuit_state == "closed"

    provider.record_failure("timeout two", category="timeout")
    assert provider.circuit_state == "soft_open"
    assert provider.is_available() is True
    assert provider.should_attempt(canary=False) is False
    assert provider.should_attempt(canary=True) is False


def test_base_provider_soft_open_probe_becomes_available_after_timeout(monkeypatch):
    import api.providers.base as base_module

    now = 1_000.0
    monkeypatch.setattr(base_module.time, "time", lambda: now)

    provider = _StubProvider("stub", {"default_model": "stub-model"})
    provider.record_failure("timeout one", category="timeout")
    provider.record_failure("timeout two", category="timeout")

    assert provider.soft_open_probe_available() is False

    monkeypatch.setattr(base_module.time, "time", lambda: now + 31.0)
    assert provider.soft_open_probe_available() is True
    assert provider.claim_soft_open_probe() is True
    assert provider.claim_soft_open_probe() is False


def test_base_provider_circuit_status_includes_cooldown_remaining_seconds(monkeypatch):
    import api.providers.base as base_module

    now = 1_000.0
    monkeypatch.setattr(base_module.time, "time", lambda: now)

    provider = _StubProvider("stub", {"default_model": "stub-model"})
    provider.record_failure("timeout one", category="timeout")
    provider.record_failure("timeout two", category="timeout")

    status = provider.circuit_status()

    assert status["state"] == "soft_open"
    assert status["cooldown_remaining_seconds"] > 0


def test_base_provider_hard_opens_on_billing_failure():
    provider = _StubProvider("stub", {"default_model": "stub-model"})

    provider.record_failure("exceeded your current quota", category="rate-limit")

    assert provider.circuit_state == "hard_open"
    assert provider.is_available() is False
    assert provider.should_attempt(canary=True) is False

    provider.record_success()
    assert provider.circuit_state == "closed"
    assert provider.is_available() is True


def test_dispatcher_resolves_provider_aliases():
    dispatcher = ProviderDispatcher()

    assert dispatcher.get_provider("google").provider_id == "gemini"
    assert dispatcher.get_provider("azure-openai").provider_id == "azure_openai"
    assert dispatcher.get_provider("vertex").provider_id == "gcp_vm"


def test_dispatcher_visible_provider_ids_include_together():
    dispatcher = ProviderDispatcher()

    visible_ids = dispatcher.provider_ids(include_hidden=False)

    assert "together" in visible_ids


def test_dispatcher_visible_order_siliconeflow_before_together():
    # siliconeflow (priority 25) is cheaper and faster than together (priority 45)
    dispatcher = ProviderDispatcher()

    visible_ids = dispatcher.provider_ids(include_hidden=False)

    assert visible_ids.index("siliconeflow") < visible_ids.index("together")


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


def test_provider_secrets_processor_redacts_nested_sensitive_fields():
    processor = provider_secrets_processor(lambda: ["sk-live-secret-12345678"])

    event = processor(
        None,
        "warning",
        {
            "event": "provider_failure",
            "provider": "openai",
            "headers": {"Authorization": "Bearer sk-live-secret-12345678"},
            "error": "failed with sk-live-secret-12345678",
        },
    )

    assert event["provider"] == "openai"
    assert event["headers"]["Authorization"] == "[REDACTED]"
    assert event["error"] == "failed with [REDACTED]"


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
    import api.providers.base as base_module

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
async def test_auto_dispatch_falls_through_to_next_healthy_candidate(
    monkeypatch,
):
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
async def test_auto_dispatch_returns_provider_none_when_all_candidates_fail(
    monkeypatch,
):
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
async def test_auto_dispatch_skips_self_hosted_candidates_by_default(
    monkeypatch,
):
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
async def test_explicit_force_fallback_provider_uses_auto_fallback_chain(
    monkeypatch,
):
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
        class_map={"local_stub": _WarmupProvider},
    )

    dispatcher.start_background_tasks()
    await asyncio.sleep(0.05)

    warmup = dispatcher._warmup_state_for("local_stub")
    assert warmup["state"] == "warm"
    assert warmup["latency_ms"] == 10.0


@pytest.mark.asyncio
async def test_dispatcher_skips_self_hosted_providers_while_warming(monkeypatch):
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
        class_map={"local_stub": _StubProvider},
    )
    dispatcher._warmup_states["local_stub"] = {"state": "warming", "latency_ms": 10.0}

    import api.providers.dispatcher_pkg.execution as execution_module

    async def fail_if_called(*args, **kwargs):
        _ = args, kwargs
        raise AssertionError("quota reservation should not be attempted for warming providers")

    monkeypatch.setattr(execution_module.quota_service, "reserve", fail_if_called)

    result = await dispatcher.dispatch(
        pid=None,
        model=None,
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is False
    assert result["error"] == "provider warming up"
    assert dispatcher._warmup_state_for("local_stub")["state"] == "warming"


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
        class_map={"openai": _StubProvider, "groq": _StubProvider},
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
        class_map={"openai": _StubProvider},
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
        class_map={"openai": _StubProvider},
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
        class_map={"openai": _StubProvider},
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
        class_map={"openai": _StubProvider},
    )
    provider = dispatcher.get_provider("openai")
    captured: dict[str, float] = {}
    original_record_success = registry.record_success

    def capture_record_success(provider_id, *, latency_ms, cost_usd):
        captured["latency_ms"] = float(latency_ms)
        return original_record_success(provider_id, latency_ms=latency_ms, cost_usd=cost_usd)

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


def test_budget_rerank_prefers_zero_cost_candidates(monkeypatch):
    dispatcher = ProviderDispatcher(
        configs={
            "openai": {"priority_tier": 30, "default_model": "gpt-4o-mini"},
            "gcp_vm": {"priority_tier": 60, "default_model": "qwen2.5:3b", "tier": "self_hosted"},
        },
        class_map={"openai": _StubProvider, "gcp_vm": _StubProvider},
    )

    monkeypatch.setattr(
        dispatcher,
        "_budget_status",
        lambda: {
            "cap_usd": 1.0,
            "current_hour_spend_usd": 2.0,
            "current_hour_spend_by_provider": {"openai": 2.0},
            "over_budget": True,
        },
    )
    monkeypatch.setattr(
        dispatcher,
        "_provider_costs",
        lambda provider_id: (0.2, 0.2) if provider_id == "openai" else (0.0, 0.0),
    )

    ranked = dispatcher._apply_budget_rerank(["openai", "gcp_vm"], routing_mode="auto")

    assert ranked == ["gcp_vm", "openai"]
