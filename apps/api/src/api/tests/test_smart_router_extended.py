"""Extended unit tests for services/smart_router.py — enums, dataclasses, CostTracker, helpers."""

from __future__ import annotations

import pytest

from api.services.smart_router import (
    CostTracker,
    ProviderCost,
    ProviderSelection,
    RoutingStrategy,
    TaskType,
    _last_user_message,
)

# ── TaskType enum ─────────────────────────────────────────────────────────────


class TestTaskType:
    def test_chat_value(self):
        assert TaskType.CHAT.value == "chat"

    def test_code_generation_value(self):
        assert TaskType.CODE_GENERATION.value == "code"

    def test_reasoning_value(self):
        assert TaskType.REASONING.value == "reasoning"

    def test_all_task_types_have_string_values(self):
        for t in TaskType:
            assert isinstance(t.value, str)

    def test_expected_count(self):
        assert len(list(TaskType)) >= 5


# ── RoutingStrategy enum ──────────────────────────────────────────────────────


class TestRoutingStrategy:
    def test_cost_optimized_value(self):
        assert RoutingStrategy.COST_OPTIMIZED.value == "cost_optimized"

    def test_quality_first_value(self):
        assert RoutingStrategy.QUALITY_FIRST.value == "quality_first"

    def test_balanced_value(self):
        assert RoutingStrategy.BALANCED.value == "balanced"

    def test_all_strategies_have_string_values(self):
        for s in RoutingStrategy:
            assert isinstance(s.value, str)


# ── ProviderCost dataclass ────────────────────────────────────────────────────


class TestProviderCost:
    def test_construction(self):
        pc = ProviderCost(input_cost=0.001, output_cost=0.002)
        assert pc.input_cost == pytest.approx(0.001)
        assert pc.output_cost == pytest.approx(0.002)

    def test_estimate_zero_tokens(self):
        pc = ProviderCost(input_cost=0.001, output_cost=0.002)
        assert pc.estimate(0, 0) == pytest.approx(0.0)

    def test_estimate_input_only(self):
        pc = ProviderCost(input_cost=1.0, output_cost=0.0)
        # 1000 input tokens at $1.0/1k = $1.00
        assert pc.estimate(1000, 0) == pytest.approx(1.0)

    def test_estimate_output_only(self):
        pc = ProviderCost(input_cost=0.0, output_cost=2.0)
        # 500 output tokens at $2.0/1k = $1.00
        assert pc.estimate(0, 500) == pytest.approx(1.0)

    def test_estimate_both(self):
        pc = ProviderCost(input_cost=1.0, output_cost=2.0)
        # 1000 input at $1.0 + 500 output at $2.0 = $1.00 + $1.00 = $2.00
        assert pc.estimate(1000, 500) == pytest.approx(2.0)

    def test_estimate_zero_cost(self):
        pc = ProviderCost(input_cost=0.0, output_cost=0.0)
        assert pc.estimate(10000, 10000) == pytest.approx(0.0)


# ── ProviderSelection dataclass ───────────────────────────────────────────────


class TestProviderSelection:
    def test_construction(self):
        ps = ProviderSelection(
            provider_id="openai",
            model="gpt-4o",
            reason="lowest cost",
            fallback_chain=["anthropic", "gemini"],
            estimated_cost=0.002,
            expected_latency_ms=800.0,
        )
        assert ps.provider_id == "openai"
        assert ps.model == "gpt-4o"
        assert len(ps.fallback_chain) == 2

    def test_empty_fallback_chain(self):
        ps = ProviderSelection(
            provider_id="anthropic",
            model="claude-sonnet-4-6",
            reason="best quality",
            fallback_chain=[],
            estimated_cost=0.005,
            expected_latency_ms=600.0,
        )
        assert ps.fallback_chain == []


# ── CostTracker ───────────────────────────────────────────────────────────────


class TestCostTracker:
    def test_default_hourly_budget(self):
        ct = CostTracker()
        assert ct.hourly_budget == pytest.approx(10.0)

    def test_custom_hourly_budget(self):
        ct = CostTracker(hourly_budget=50.0)
        assert ct.hourly_budget == pytest.approx(50.0)

    def test_initial_spend_is_zero(self):
        ct = CostTracker()
        assert ct.current_hour_spend == pytest.approx(0.0)

    def test_budget_remaining_starts_at_full(self):
        ct = CostTracker(hourly_budget=10.0)
        assert ct.budget_remaining() == pytest.approx(10.0)

    def test_should_use_cheaper_false_when_no_spend(self):
        ct = CostTracker()
        assert ct.should_use_cheaper_provider() is False

    def test_should_use_cheaper_true_when_over_70_percent(self):
        ct = CostTracker(hourly_budget=10.0)
        ct.current_hour_spend = 7.5  # 75% of budget
        assert ct.should_use_cheaper_provider() is True

    def test_should_use_cheaper_false_at_exactly_70_percent(self):
        ct = CostTracker(hourly_budget=10.0)
        ct.current_hour_spend = 7.0  # exactly 70%
        assert ct.should_use_cheaper_provider() is False

    def test_budget_remaining_clamped_to_zero(self):
        ct = CostTracker(hourly_budget=5.0)
        ct.current_hour_spend = 100.0
        assert ct.budget_remaining() == pytest.approx(0.0)

    def test_get_status_returns_required_keys(self):
        ct = CostTracker()
        status = ct.get_status()
        assert "hourly_budget" in status
        assert "current_spend" in status
        assert "remaining" in status
        assert "request_count" in status
        assert "should_use_cheaper" in status

    def test_get_status_request_count_starts_zero(self):
        ct = CostTracker()
        status = ct.get_status()
        assert status["request_count"] == 0

    def test_request_history_empty_initially(self):
        ct = CostTracker()
        assert ct.request_history == []

    def test_estimate_cost_unknown_provider_returns_zero(self):
        ct = CostTracker()
        cost = ct.estimate_cost("totally_unknown_provider_xyz", estimated_tokens=500)
        assert cost == pytest.approx(0.0)


# ── _last_user_message helper ─────────────────────────────────────────────────


class TestLastUserMessage:
    def test_empty_list_returns_empty_string(self):
        assert _last_user_message([]) == ""

    def test_none_returns_empty_string(self):
        assert _last_user_message(None) == ""

    def test_single_user_message_returned(self):
        msgs = [{"role": "user", "content": "hello"}]
        assert _last_user_message(msgs) == "hello"

    def test_last_user_message_returned_not_first(self):
        msgs = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "response"},
            {"role": "user", "content": "second"},
        ]
        assert _last_user_message(msgs) == "second"

    def test_no_user_message_returns_empty(self):
        msgs = [
            {"role": "assistant", "content": "hi"},
            {"role": "system", "content": "you are helpful"},
        ]
        assert _last_user_message(msgs) == ""

    def test_non_string_content_returns_empty(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": "complex"}]}]
        assert _last_user_message(msgs) == ""

    def test_non_dict_message_skipped(self):
        msgs = ["not a dict", {"role": "user", "content": "valid"}]
        assert _last_user_message(msgs) == "valid"

    def test_missing_content_returns_empty_string(self):
        msgs = [{"role": "user"}]
        assert _last_user_message(msgs) == ""
