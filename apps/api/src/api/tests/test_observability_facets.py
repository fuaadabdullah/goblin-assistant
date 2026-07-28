from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.services.observability_facets import (
    ContextSnapshotFacet,
    MemoryPromotionFacet,
    ObservabilityDashboardFacet,
    RetrievalTraceFacet,
    WriteTimeFacet,
)
from api.services.observability_models import PromotionDecision


class _Owner:
    def __init__(self):
        self.write_decisions = []
        self.memory_promotions = []
        self.retrieval_traces = []
        self.context_snapshots = []
        self.memory_health = {
            "promotion_rejection_rate": 0.0,
            "contradiction_rate": 0.0,
            "decay_events": 0,
        }
        self.retrieval_quality = {
            "avg_chunks_per_request": 0,
            "token_utilization_percent": 0,
            "retrieval_hit_rate": 0,
        }
        self.cost_control = {
            "embeddings_per_conversation": 0,
            "tokens_spent_per_tier": {},
            "cache_hit_rate": 0,
        }


@pytest.mark.asyncio
async def test_write_time_facet_records_legacy_payload(monkeypatch):
    owner = _Owner()
    facet = WriteTimeFacet(owner)

    from api.observability.decision_logger import decision_logger as _dl

    monkeypatch.setattr(_dl, "log_decision", AsyncMock(return_value=None))

    facet.log_write_time_decision(
        message_id="msg-1",
        user_id="user-1",
        conversation_id="conv-1",
        message_content="Short text",
        message_role="user",
        write_time_result={
            "classification": {"type": "task_result", "confidence": 0.9},
            "decision": {
                "actions": [SimpleNamespace(value="embed"), SimpleNamespace(value="cache")]
            },
        },
    )

    assert owner.write_decisions[0]["message_id"] == "msg-1"
    assert owner.write_decisions[0]["classified_type"] == "task_result"
    assert owner.write_decisions[0]["decisions"]["embedded"] is True


@pytest.mark.asyncio
async def test_memory_promotion_facet_redacts_and_caches(monkeypatch):
    owner = _Owner()
    facet = MemoryPromotionFacet(owner)

    from api.observability.memory_logger import memory_promotion_logger as _ml

    monkeypatch.setattr(_ml, "log_promotion_attempt", AsyncMock(return_value=None))

    facet.log_memory_promotion_event(
        candidate_text="a" * 140,
        source="summary",
        confidence_score=0.8,
        promotion_decision=PromotionDecision.REJECTED,
        rejection_reason="not enough evidence",
        user_id="user-1",
        conversation_id="conv-1",
    )

    assert owner.memory_promotions[0].candidate_text.endswith("[REDACTED]...")
    assert len(owner.memory_promotions) == 1


@pytest.mark.asyncio
async def test_retrieval_trace_facet_records_trace(monkeypatch):
    owner = _Owner()
    facet = RetrievalTraceFacet(owner)

    from api.observability.retrieval_tracer import retrieval_tracer as _rt

    monkeypatch.setattr(_rt, "trace_retrieval", AsyncMock(return_value=None))

    facet.log_retrieval_trace(
        request_id="req-1",
        user_id="user-1",
        model_selected="model-a",
        token_budget=1000,
        retrieval_result={
            "layers": [
                {"name": "memory", "tokens": 10, "score": 0.9, "original_tokens": 10},
                {"name": "summary", "tokens": 8, "score": 0.8, "original_tokens": 12},
            ]
        },
    )

    assert owner.retrieval_traces[0].request_id == "req-1"
    assert owner.retrieval_traces[0].items_retrieved[1]["truncated"] is True


@pytest.mark.asyncio
async def test_context_snapshot_facet_records_snapshot(monkeypatch):
    owner = _Owner()
    facet = ContextSnapshotFacet(owner)

    from api.observability.context_snapshotter import context_snapshotter as _cs

    monkeypatch.setattr(_cs, "create_snapshot", AsyncMock(return_value="snapshot-id"))

    facet.log_context_assembly_snapshot(
        request_id="req-1",
        user_id="user-1",
        conversation_id="conv-1",
        context_assembly={
            "context": "hello",
            "layers": [{"name": "system", "tokens": 3}],
            "total_tokens_used": 3,
            "remaining_tokens": 5,
        },
    )

    assert owner.context_snapshots[0].request_id == "req-1"
    assert owner.context_snapshots[0].total_token_usage == 3


def test_dashboard_facets_respects_manual_metric_overrides():
    owner = _Owner()
    owner.memory_health["promotion_rejection_rate"] = 0.85
    owner.retrieval_quality["retrieval_hit_rate"] = 0.05
    facet = ObservabilityDashboardFacet(owner)

    alerts = facet.check_alerts()
    alert_types = {alert["type"] for alert in alerts}

    assert "memory_promotion_spike" in alert_types
    assert "retrieval_empty" in alert_types
