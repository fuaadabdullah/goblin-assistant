"""Tests for ProviderDispatcher routing, aliases, and candidate ordering."""

import asyncio
import re
from unittest.mock import AsyncMock

import pytest

from api.providers.dispatcher import ProviderDispatcher
from api.routing.router import hybrid_router, registry

from .conftest import StubProvider

dispatcher_module = __import__("api.providers.dispatcher", fromlist=["_"])


def test_dispatcher_routing_aliases_and_budget_rerank(monkeypatch):
    dispatcher = ProviderDispatcher()

    monkeypatch.setattr(
        dispatcher_module,
        "_MODEL_ALIASES",
        {"claude-haiku": ("anthropic", "claude-3-5-haiku-latest")},
    )
    monkeypatch.setattr(
        dispatcher_module,
        "_MODEL_ALIAS_PATTERNS",
        [(re.compile(r"^gpt-mini-(.+)$"), "openai", "gpt-4o-mini-{1}")],
    )
    monkeypatch.setattr(
        dispatcher,
        "list_providers",
        lambda include_hidden=False: [
            {
                "id": "openai",
                "name": "OpenAI",
                "priority_tier": 2,
                "tier": "cloud",
                "local_routing": False,
                "hidden": False,
                "capabilities": ["chat"],
                "default_model": "gpt-4o-mini",
            },
            {
                "id": "groq",
                "name": "Groq",
                "priority_tier": 1,
                "tier": "cloud",
                "local_routing": True,
                "hidden": False,
                "capabilities": ["chat"],
                "default_model": "llama-3.3-70b-versatile",
            },
            {
                "id": "vision",
                "name": "Vision",
                "priority_tier": 3,
                "tier": "cloud",
                "local_routing": False,
                "hidden": False,
                "capabilities": ["vision"],
                "default_model": "vision-1",
            },
        ],
    )
    monkeypatch.setattr(dispatcher, "is_configured", lambda provider_id: provider_id != "vision")
    monkeypatch.setattr(dispatcher, "_local_order", lambda: ["groq", "openai"])
    monkeypatch.setattr(dispatcher, "_cheapest_order", lambda: ["openai", "groq"])
    monkeypatch.setattr(dispatcher, "_budget_status", lambda: {"over_budget": False})

    assert dispatcher.top_providers_for("chat") == ["openai", "groq"]
    assert dispatcher.top_providers_for("chat", prefer_local=True) == ["groq", "openai"]
    assert dispatcher.top_providers_for("chat", prefer_cost=True) == ["openai", "groq"]
    assert dispatcher.top_providers_for("chat", limit=1) == ["openai"]

    assert dispatcher._resolve_pattern_model_alias("gpt-mini-coder") == (
        "openai",
        "gpt-4o-mini-coder",
    )
    assert dispatcher._resolve_model_alias(None, "claude-haiku") == (
        "anthropic",
        "claude-3-5-haiku-latest",
    )
    assert dispatcher._resolve_model_alias("anthropic", "claude-haiku") == (
        "anthropic",
        "claude-3-5-haiku-latest",
    )
    assert dispatcher._resolve_model_alias("openai", "gpt-mini-coder") == (
        "openai",
        "gpt-4o-mini-coder",
    )

    monkeypatch.setattr(
        dispatcher,
        "_budget_status",
        lambda: {
            "over_budget": True,
            "current_hour_spend_usd": 10.0,
            "cap_usd": 8.0,
        },
    )
    monkeypatch.setattr(
        dispatcher,
        "_provider_costs",
        lambda provider_id: (0.0, 0.0) if provider_id == "groq" else (0.1, 0.2),
    )
    assert dispatcher._apply_budget_rerank(["openai", "groq"], routing_mode="auto") == [
        "groq",
        "openai",
    ]


def test_candidate_order_auto_uses_hybrid_router(monkeypatch):
    dispatcher = ProviderDispatcher()

    monkeypatch.setattr(
        dispatcher,
        "list_providers",
        lambda include_hidden=False: [
            {"id": "p1", "priority_tier": 1, "tier": "cloud", "local_routing": False},
            {"id": "p2", "priority_tier": 2, "tier": "cloud", "local_routing": False},
        ],
    )
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
async def test_health_inventory_times_out_hung_provider(monkeypatch):
    from api.providers.base import ProviderHealth

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


@pytest.mark.asyncio
async def test_dispatcher_inventory_debug_and_module_helpers(monkeypatch):
    dispatcher = ProviderDispatcher()

    monkeypatch.setattr(
        dispatcher,
        "list_providers",
        lambda include_hidden=False: [
            {
                "id": "openai",
                "name": "OpenAI",
                "priority_tier": 1,
                "tier": "cloud",
                "local_routing": False,
                "hidden": False,
                "capabilities": ["chat"],
                "default_model": "gpt-4o-mini",
            },
            {
                "id": "groq",
                "name": "Groq",
                "priority_tier": 2,
                "tier": "cloud",
                "local_routing": True,
                "hidden": False,
                "capabilities": ["chat"],
                "default_model": "llama-3.3-70b-versatile",
            },
        ],
    )

    async def _check_provider(provider_id: str):
        if provider_id == "groq":
            raise RuntimeError("provider token=sk-secret")
        return {
            "configured": True,
            "healthy": True,
            "health": "healthy",
            "health_reason": "",
            "is_selectable": True,
            "latency_ms": 11.0,
            "circuit_breaker": {"state": "closed"},
        }

    monkeypatch.setattr(dispatcher, "check_provider", _check_provider)
    inventory = await dispatcher.get_provider_inventory(include_hidden=False)
    assert len(inventory) == 2
    assert inventory[0]["healthy"] is True
    assert inventory[1]["healthy"] is False

    health_all = await dispatcher.health_all(include_hidden=False)
    assert health_all["openai"]["healthy"] is True
    assert health_all["groq"]["healthy"] is False

    monkeypatch.setattr(dispatcher, "is_configured", lambda provider_id: provider_id == "openai")
    monkeypatch.setattr(dispatcher, "_warmup_state_for", lambda provider_id: {"state": provider_id})
    monkeypatch.setattr(dispatcher, "_budget_status", lambda: {"over_budget": False})
    monkeypatch.setattr(
        registry,
        "snapshot",
        lambda: {"openai": {"success_rate": 1.0}},
    )
    monkeypatch.setattr(registry, "metrics_snapshot", lambda: {"calls": 1})
    monkeypatch.setattr(registry, "persisted_snapshot", lambda: {"persisted": True})
    monkeypatch.setattr(registry, "persistence_status", lambda: {"enabled": True})

    debug = dispatcher.debug_info()
    assert debug["routing_table"][0]["configured"] is True
    assert debug["registry_stats"] == {"openai": {"success_rate": 1.0}}

    monkeypatch.setattr(
        dispatcher_module.dispatcher, "health_all", AsyncMock(return_value={"ok": True})
    )
    monkeypatch.setattr(
        dispatcher_module.dispatcher,
        "list_providers",
        lambda include_hidden=False: [{"id": "openai"}],
    )
    monkeypatch.setattr(dispatcher_module.dispatcher, "debug_info", lambda: {"debug": True})

    assert await dispatcher_module.get_provider_health() == {"ok": True}
    assert dispatcher_module.list_providers() == [{"id": "openai"}]
    assert dispatcher_module.get_debug_info() == {"debug": True}


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
    class CountingProvider(StubProvider):
        inits = 0

        def __init__(self, provider_id, config=None):
            CountingProvider.inits += 1
            super().__init__(provider_id, config)

    provider_class_map = dispatcher_module.__dict__["_PROVIDER_CLASS_MAP"]
    monkeypatch.setitem(provider_class_map, "openai", CountingProvider)
    dispatcher = ProviderDispatcher()

    assert CountingProvider.inits == 0
    dispatcher.get_provider("openai")
    assert CountingProvider.inits == 1
