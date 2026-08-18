"""Tests for api.services.smart_router."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.smart_router import (
    CostTracker,
    ProviderCost,
    RoutingStrategy,
    SmartRouter,
    TaskType,
)


def test_provider_cost_estimate_calculates_expected_value():
    cost = ProviderCost(input_cost=2.0, output_cost=4.0)

    assert cost.estimate(1000, 500) == 4.0


def test_cost_tracker_budget_status_updates():
    tracker = CostTracker(hourly_budget=10.0)
    tracker.current_hour_spend = 8.0

    assert tracker.budget_remaining() == 2.0
    assert tracker.should_use_cheaper_provider() is True


def test_cost_tracker_get_status_contains_expected_fields():
    tracker = CostTracker(hourly_budget=10.0)
    status = tracker.get_status()

    assert status["hourly_budget"] == 10.0
    assert "current_spend" in status
    assert "remaining" in status


def test_resolve_task_type_consumes_prompt_classifier_label():
    router = SmartRouter(strategy=RoutingStrategy.BALANCED)

    assert (
        router._resolve_task_type(
            None,
            [{"role": "user", "content": "Summarize this release note"}],
        )
        == TaskType.SUMMARIZATION.value
    )


def test_ml_bandit_strategy_enters_routing_prompt_adapter():
    router = SmartRouter(strategy=RoutingStrategy.ML_BANDIT)
    intent = SimpleNamespace(label=SimpleNamespace(value="coding"), confidence=0.82)

    with (
        patch(
            "api.services.smart_router.top_providers_for",
            return_value=["openai", "anthropic"],
        ),
        patch(
            "api.services.smart_router.dispatcher.get_provider",
            return_value=MagicMock(config={}),
        ),
        patch(
            "api.routing.learning_adapters.rank_prompt_with_bandit_router",
            return_value=["anthropic", "openai"],
        ) as rank_prompt,
    ):
        result = router._ordered_candidates(
            RoutingStrategy.ML_BANDIT,
            "coding",
            messages=[{"role": "user", "content": "Please refactor this class"}],
            intent=intent,
            request_id="smart-route-1",
        )

    assert result == ["anthropic", "openai"]
    rank_prompt.assert_called_once()
    args, kwargs = rank_prompt.call_args
    assert args[0] == ["openai", "anthropic"]
    assert kwargs["task_type"] == "coding"
    assert kwargs["prompt"] == "Please refactor this class"
    assert kwargs["intent_label"] == "coding"
    assert kwargs["intent_confidence"] == 0.82
    assert kwargs["request_id"] == "smart-route-1"


@pytest.mark.asyncio
async def test_invoke_with_fallback_returns_success():
    router = SmartRouter(strategy=RoutingStrategy.BALANCED)

    fake_provider = MagicMock()
    fake_provider.default_model = "gpt-4o-mini"

    with (
        patch(
            "api.services.smart_router.top_providers_for",
            return_value=["openai"],
        ),
        patch(
            "api.services.smart_router.dispatcher.get_provider",
            return_value=fake_provider,
        ),
        patch(
            "api.services.smart_router.dispatcher.get_provider_config",
            return_value={"default_model": "gpt-4o-mini"},
        ),
        patch(
            "api.services.smart_router.health_monitor.is_available",
            return_value=True,
        ),
        patch(
            "api.services.smart_router.health_monitor.get_latency",
            return_value=42,
        ),
        patch(
            "api.services.smart_router.registry.record_failure",
        ),
    ):
        result = await router.invoke_with_fallback(
            AsyncMock(return_value={"ok": True, "result": {"usage": {}}}),
            messages=[{"role": "user", "content": "hi"}],
            task_type="chat",
        )

    assert result["ok"] is True
    assert result["routing"]["provider"] == "openai"


@pytest.mark.asyncio
async def test_select_provider_prefers_healthy_preferred_provider():
    router = SmartRouter(strategy=RoutingStrategy.BALANCED)

    fake_provider = MagicMock()
    fake_provider.default_model = "gpt-4o-mini"

    with (
        patch(
            "api.services.smart_router.health_monitor.is_available",
            return_value=True,
        ),
        patch(
            "api.services.smart_router.health_monitor.get_latency",
            return_value=12,
        ),
        patch(
            "api.services.smart_router.dispatcher.get_provider_config",
            return_value={"default_model": "gpt-4o-mini"},
        ),
        patch(
            "api.services.smart_router.dispatcher.get_provider",
            return_value=fake_provider,
        ),
        patch(
            "api.services.smart_router.dispatcher.get_provider_inventory",
            return_value=[],
        ),
    ):
        selection = await router.select_provider(preferred_provider="openai")

    assert selection.provider_id == "openai"
    assert selection.reason == "Preferred provider selected"


@pytest.mark.asyncio
async def test_select_provider_returns_emergency_selection_when_no_candidates():
    router = SmartRouter(strategy=RoutingStrategy.BALANCED)

    with patch(
        "api.services.smart_router.top_providers_for",
        return_value=[],
    ):
        selection = await router.select_provider(task_type="chat")

    assert selection.provider_id == "mock"
    assert selection.reason.startswith("No providers available")


def test_get_status_includes_cost_tracking_and_router_state():
    router = SmartRouter(strategy=RoutingStrategy.COST_OPTIMIZED)

    with (
        patch(
            "api.services.smart_router.health_monitor.get_healthy_providers",
            return_value=["openai"],
        ),
        patch(
            "api.services.smart_router.health_monitor.get_available_providers",
            return_value=["openai"],
        ),
        patch(
            "api.services.smart_router.health_monitor.get_best_providers",
            return_value=["openai"],
        ),
        patch(
            "api.services.smart_router.registry.snapshot",
            return_value={"openai": {"requests": 1}},
        ),
    ):
        status = router.get_status()

    assert status["strategy"] == "cost_optimized"
    assert status["healthy_providers"] == ["openai"]
    assert status["routing_registry"] == {"openai": {"requests": 1}}
