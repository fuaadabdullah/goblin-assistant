from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from api.observability.retrieval_tracer import RetrievalTracer, RetrievedItem
from api.observability.retrieval_tracer_helpers import (
    calculate_tier_breakdown,
    identify_truncations,
)


def _item(
    *,
    source: str = "semantic_retrieval",
    score: float = 0.8,
    tokens: int = 20,
    truncated: bool = False,
) -> RetrievedItem:
    return RetrievedItem(
        source=source,
        source_id="item-1",
        content="content",
        relevance_score=score,
        token_count=tokens,
        rank=1,
        truncated=truncated,
        metadata={},
    )


def test_calculate_tier_breakdown_aggregates_counts_and_scores():
    stats = calculate_tier_breakdown(
        [
            _item(source="semantic_retrieval", score=0.9, tokens=10),
            _item(source="semantic_retrieval", score=0.3, tokens=20, truncated=True),
            _item(source="working_memory", score=0.7, tokens=5),
        ]
    )

    assert stats["semantic_retrieval"]["count"] == 2
    assert stats["semantic_retrieval"]["total_tokens"] == 30
    assert stats["semantic_retrieval"]["avg_relevance"] == 0.6
    assert stats["semantic_retrieval"]["truncated_count"] == 1
    assert stats["working_memory"]["count"] == 1


def test_identify_truncations_reports_item_and_budget_overflow():
    truncations = identify_truncations(
        [
            _item(tokens=90, truncated=True),
            _item(tokens=40),
        ],
        token_budget=100,
    )

    assert truncations[0]["reason"] == "token_budget_exceeded"
    assert truncations[1]["reason"] == "total_context_exceeded_budget"


@pytest.mark.asyncio
async def test_trace_retrieval_caches_trace_and_exposes_history(monkeypatch):
    tracer = RetrievalTracer()
    monkeypatch.setattr(tracer, "_log_retrieval_structured", lambda trace: None)
    monkeypatch.setattr(tracer, "_log_to_file", lambda trace: None)
    tracer.config["observability"]["log_retrievals_to_file"] = False

    await tracer.trace_retrieval(
        request_id="req-1",
        user_id="user-1",
        model_selected="model-a",
        token_budget=100,
        items_retrieved=[_item(tokens=20)],
        context_hash="hash",
        context_snapshot="snapshot text",
        retrieval_time_ms=12.5,
    )

    assert "req-1" in tracer._trace_cache
    history = await tracer.get_retrieval_history(user_id="user-1")
    assert len(history) == 1
    assert history[0]["request_id"] == "req-1"


@pytest.mark.asyncio
async def test_search_and_stats_filter_current_trace_cache(monkeypatch):
    tracer = RetrievalTracer()
    monkeypatch.setattr(tracer, "_log_retrieval_structured", lambda trace: None)
    monkeypatch.setattr(tracer, "_log_to_file", lambda trace: None)
    tracer.config["observability"]["log_retrievals_to_file"] = False

    now = datetime.utcnow()
    trace = await tracer.trace_retrieval(
        request_id="req-2",
        user_id="user-2",
        model_selected="model-b",
        token_budget=100,
        items_retrieved=[_item(tokens=25, score=0.75)],
        context_hash="hash-2",
        context_snapshot="needle in snapshot",
        retrieval_time_ms=20,
    )
    trace.timestamp = now - timedelta(minutes=5)

    results = await tracer.search_retrievals(query="needle", user_id="user-2")
    assert len(results) == 1

    stats = await tracer.get_retrieval_stats(user_id="user-2", time_window_hours=1)
    assert stats["total_retrievals"] == 1
    assert stats["retrieval_quality"]["avg_items_per_retrieval"] == 1.0

    report = await tracer.get_retrieval_quality_report(user_id="user-2")
    assert report["quality_status"] in {"good", "warning", "poor"}
