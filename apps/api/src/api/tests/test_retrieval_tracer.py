"""Tests for observability/retrieval_tracer.py — dataclasses, enums, and RetrievalTracer."""

from __future__ import annotations

import json
from datetime import datetime

from api.observability.retrieval_tracer import (
    RetrievalTier,
    RetrievalTrace,
    RetrievedItem,
)

# ── RetrievalTier enum ────────────────────────────────────────────────────────


class TestRetrievalTier:
    def test_system_value(self):
        assert RetrievalTier.SYSTEM.value == "system"

    def test_long_term_memory_value(self):
        assert RetrievalTier.LONG_TERM_MEMORY.value == "long_term_memory"

    def test_working_memory_value(self):
        assert RetrievalTier.WORKING_MEMORY.value == "working_memory"

    def test_semantic_retrieval_value(self):
        assert RetrievalTier.SEMANTIC_RETRIEVAL.value == "semantic_retrieval"

    def test_ephemeral_memory_value(self):
        assert RetrievalTier.EPHEMERAL_MEMORY.value == "ephemeral_memory"

    def test_all_five_tiers(self):
        assert len(list(RetrievalTier)) == 5


# ── RetrievedItem dataclass ───────────────────────────────────────────────────


def _make_item(
    source: str = "long_term",
    content: str = "fact about user",
    relevance_score: float = 0.9,
    token_count: int = 20,
    rank: int = 0,
    truncated: bool = False,
) -> RetrievedItem:
    return RetrievedItem(
        source=source,
        source_id="item-1",
        content=content,
        relevance_score=relevance_score,
        token_count=token_count,
        rank=rank,
        truncated=truncated,
        metadata={"tier": "long_term_memory"},
    )


class TestRetrievedItem:
    def test_construction(self):
        item = _make_item()
        assert item.source == "long_term"
        assert item.content == "fact about user"

    def test_to_dict_returns_dict(self):
        item = _make_item()
        d = item.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_all_fields(self):
        item = _make_item()
        d = item.to_dict()
        assert "source" in d
        assert "content" in d
        assert "relevance_score" in d
        assert "token_count" in d
        assert "rank" in d
        assert "truncated" in d
        assert "metadata" in d

    def test_to_dict_preserves_values(self):
        item = _make_item(content="test content", rank=3, truncated=True)
        d = item.to_dict()
        assert d["content"] == "test content"
        assert d["rank"] == 3
        assert d["truncated"] is True

    def test_none_source_id_preserved(self):
        item = RetrievedItem(
            source="ephemeral",
            source_id=None,
            content="temp",
            relevance_score=0.5,
            token_count=5,
            rank=0,
            truncated=False,
            metadata={},
        )
        assert item.source_id is None
        assert item.to_dict()["source_id"] is None


# ── RetrievalTrace dataclass ──────────────────────────────────────────────────


def _make_trace(items=None) -> RetrievalTrace:
    return RetrievalTrace(
        request_id="req-abc",
        user_id="user-1",
        timestamp=datetime(2026, 6, 10, 12, 0, 0),
        model_selected="claude-sonnet-4-6",
        token_budget=4096,
        total_tokens_used=512,
        items_retrieved=items or [],
        tier_breakdown={"long_term": {"count": 2, "tokens": 100}},
        context_hash="abc123",
        context_snapshot="snapshot...",
        retrieval_time_ms=42.5,
        truncation_events=[],
        error=None,
    )


class TestRetrievalTrace:
    def test_construction(self):
        trace = _make_trace()
        assert trace.request_id == "req-abc"
        assert trace.model_selected == "claude-sonnet-4-6"

    def test_to_dict_returns_dict(self):
        trace = _make_trace()
        d = trace.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_timestamp_as_string(self):
        trace = _make_trace()
        d = trace.to_dict()
        assert isinstance(d["timestamp"], str)

    def test_to_dict_includes_items_retrieved(self):
        items = [_make_item()]
        trace = _make_trace(items=items)
        d = trace.to_dict()
        assert len(d["items_retrieved"]) == 1
        assert isinstance(d["items_retrieved"][0], dict)

    def test_to_dict_with_error_field(self):
        trace_with_error = RetrievalTrace(
            request_id="req-err",
            user_id="user-1",
            timestamp=datetime(2026, 6, 10, 12, 0, 0),
            model_selected="gpt-4o",
            token_budget=4096,
            total_tokens_used=0,
            items_retrieved=[],
            tier_breakdown={},
            context_hash="",
            context_snapshot="",
            retrieval_time_ms=0.0,
            truncation_events=[],
            error="retrieval failed",
        )
        d = trace_with_error.to_dict()
        assert d["error"] == "retrieval failed"

    def test_to_json_returns_valid_json(self):
        trace = _make_trace()
        json_str = trace.to_json()
        parsed = json.loads(json_str)
        assert parsed["request_id"] == "req-abc"

    def test_to_json_contains_timestamp(self):
        trace = _make_trace()
        json_str = trace.to_json()
        parsed = json.loads(json_str)
        assert "timestamp" in parsed

    def test_to_json_with_multiple_items(self):
        items = [_make_item(content=f"item {i}", rank=i) for i in range(3)]
        trace = _make_trace(items=items)
        json_str = trace.to_json()
        parsed = json.loads(json_str)
        assert len(parsed["items_retrieved"]) == 3

    def test_to_json_utf8_content(self):
        item = RetrievedItem(
            source="memory",
            source_id=None,
            content="日本語テスト",
            relevance_score=0.8,
            token_count=10,
            rank=0,
            truncated=False,
            metadata={},
        )
        trace = _make_trace(items=[item])
        json_str = trace.to_json()
        assert "日本語テスト" in json_str

    def test_none_user_id_preserved(self):
        trace2 = RetrievalTrace(
            request_id="req-anon",
            user_id=None,
            timestamp=datetime(2026, 6, 10, 12, 0, 0),
            model_selected="claude-haiku-4-5",
            token_budget=2048,
            total_tokens_used=100,
            items_retrieved=[],
            tier_breakdown={},
            context_hash="",
            context_snapshot="",
            retrieval_time_ms=5.0,
            truncation_events=[],
            error=None,
        )
        d = trace2.to_dict()
        assert d["user_id"] is None


# ── RetrievalTracer (limited — uses get_system_config) ────────────────────────


class TestRetrievalTracerImport:
    def test_retrieval_tracer_importable(self):
        from api.observability.retrieval_tracer import RetrievalTracer

        assert RetrievalTracer is not None

    def test_trace_retrieval_function_importable(self):
        from api.observability.retrieval_tracer import trace_retrieval

        assert callable(trace_retrieval)

    def test_retrieval_tracer_singleton_importable(self):
        from api.observability.retrieval_tracer import RetrievalTracer, retrieval_tracer

        assert isinstance(retrieval_tracer, RetrievalTracer)
