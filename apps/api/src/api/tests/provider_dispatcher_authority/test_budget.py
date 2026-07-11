"""Tests for ProviderDispatcher budget reranking behavior."""

from api.providers.dispatcher import ProviderDispatcher

from .conftest import StubProvider


def test_budget_rerank_prefers_zero_cost_candidates(monkeypatch):
    dispatcher = ProviderDispatcher(
        configs={
            "openai": {"priority_tier": 30, "default_model": "gpt-4o-mini"},
            "gcp_vm": {"priority_tier": 60, "default_model": "qwen2.5:3b", "tier": "self_hosted"},
        },
        class_map={"openai": StubProvider, "gcp_vm": StubProvider},
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
