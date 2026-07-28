"""Tests for RetrievalMetricsService — aggregation, window filtering, percentile math."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from api.services.retrieval_metrics_service import (
    FAILURE_EMBEDDING_UNAVAILABLE,
    FAILURE_LAYER_SKIPPED,
    FAILURE_TRUNCATION_TRIGGERED,
    RetrievalMetricsService,
)


@pytest.fixture
def svc() -> RetrievalMetricsService:
    return RetrievalMetricsService()


# ---------------------------------------------------------------------------
# Token budget accuracy (Q1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_delta_zero_when_exact(svc):
    svc.record_token_accuracy("u1", predicted=500, actual=500)
    result = await svc.get_token_budget_accuracy()
    assert result["avg_delta"] == 0.0
    assert result["pct_within_5pct"] == 100.0


@pytest.mark.asyncio
async def test_token_delta_positive_when_assembly_over(svc):
    svc.record_token_accuracy("u1", predicted=1000, actual=1060)
    result = await svc.get_token_budget_accuracy()
    assert result["avg_delta"] == 60.0


@pytest.mark.asyncio
async def test_token_delta_negative_when_under(svc):
    svc.record_token_accuracy("u1", predicted=1000, actual=950)
    result = await svc.get_token_budget_accuracy()
    assert result["avg_delta"] == -50.0


@pytest.mark.asyncio
async def test_pct_within_5pct_threshold(svc):
    svc.record_token_accuracy("u1", predicted=1000, actual=1049)  # 4.9% — within
    svc.record_token_accuracy("u1", predicted=1000, actual=1051)  # 5.1% — outside
    result = await svc.get_token_budget_accuracy()
    assert result["pct_within_5pct"] == 50.0


@pytest.mark.asyncio
async def test_token_accuracy_empty_window(svc):
    result = await svc.get_token_budget_accuracy()
    assert result["sample_count"] == 0


@pytest.mark.asyncio
async def test_token_accuracy_window_filter(svc):
    svc.record_token_accuracy("u1", predicted=500, actual=510)
    # Backdate one event beyond the window
    old_event = svc._token_accuracy_events[-1].copy()
    old_event["ts"] = datetime.utcnow() - timedelta(hours=25)
    old_event["delta"] = 999
    svc._token_accuracy_events.append(old_event)

    result = await svc.get_token_budget_accuracy(window_hours=24)
    # Only the first event (delta=10) should be in window
    assert result["sample_count"] == 1
    assert result["avg_delta"] == 10.0


# ---------------------------------------------------------------------------
# Tier latency (Q2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tier_latency_all_five_tiers(svc):
    svc.record_retrieval_timing(
        "u1",
        {
            "long_term": 12.5,
            "summary": 8.1,
            "index": 45.0,
            "messages": 22.3,
            "recent": 5.5,
        },
    )
    result = await svc.get_tier_latency_breakdown()
    assert set(result["tiers"].keys()) == {"long_term", "summary", "index", "messages", "recent"}


@pytest.mark.asyncio
async def test_tier_latency_p95_computed(svc):
    # Push 20 events with values 1–20 ms for a single tier
    for i in range(1, 21):
        svc.record_retrieval_timing("u1", {"long_term": float(i)})

    result = await svc.get_tier_latency_breakdown()
    lt = result["tiers"]["long_term"]
    # p95 of [1..20] → index = int(20 * 0.95) = 19 → sorted[19] = 20.0
    assert lt["p95_ms"] == 20.0
    assert lt["sample_count"] == 20


@pytest.mark.asyncio
async def test_assembly_latency_aggregated(svc):
    svc.record_assembly_latency("u1", 100.0)
    svc.record_assembly_latency("u1", 200.0)
    result = await svc.get_tier_latency_breakdown()
    assert result["assembly_total"]["avg_ms"] == 150.0
    assert result["assembly_total"]["sample_count"] == 2


@pytest.mark.asyncio
async def test_tier_latency_empty(svc):
    result = await svc.get_tier_latency_breakdown()
    assert result["tiers"] == {}
    assert result["assembly_total"]["sample_count"] == 0


# ---------------------------------------------------------------------------
# Cache hit rate (Q3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cache_hit_rate_delegates_to_cache_service(svc, monkeypatch):
    mock_cache = MagicMock()
    mock_cache.get_hit_rate.return_value = {"hits": 3, "misses": 1, "rate": 0.75, "total": 4}
    import api.services.retrieval_metrics_service as rms_mod

    monkeypatch.setattr(rms_mod, "cache_service", mock_cache, raising=False)

    # Patch the import inside the method
    import api.services.cache_service as cs_mod

    original = cs_mod.cache_service
    cs_mod.cache_service = mock_cache

    result = await svc.get_cache_hit_rate()
    assert result["rate"] == 0.75
    assert result["total"] == 4

    cs_mod.cache_service = original


# ---------------------------------------------------------------------------
# Failure summary (Q4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failure_summary_counts_by_type(svc):
    svc.record_failure("u1", FAILURE_EMBEDDING_UNAVAILABLE, "semantic_retrieval")
    svc.record_failure("u1", FAILURE_EMBEDDING_UNAVAILABLE, "semantic_retrieval")
    svc.record_failure("u1", FAILURE_LAYER_SKIPPED, "long_term_memory")
    svc.record_failure("u1", FAILURE_TRUNCATION_TRIGGERED, "ephemeral")

    result = await svc.get_failure_summary()
    assert result["by_type"][FAILURE_EMBEDDING_UNAVAILABLE] == 2
    assert result["by_type"][FAILURE_LAYER_SKIPPED] == 1
    assert result["by_type"][FAILURE_TRUNCATION_TRIGGERED] == 1
    assert result["sample_count"] == 4


@pytest.mark.asyncio
async def test_failure_summary_counts_by_layer(svc):
    svc.record_failure("u1", FAILURE_LAYER_SKIPPED, "long_term_memory", detail="skip_no_data")
    svc.record_failure(
        "u1", FAILURE_LAYER_SKIPPED, "long_term_memory", detail="skip_budget_exhausted"
    )
    svc.record_failure("u1", FAILURE_LAYER_SKIPPED, "working_memory", detail="skip_no_data")

    result = await svc.get_failure_summary()
    assert result["by_layer"]["long_term_memory"] == 2
    assert result["by_layer"]["working_memory"] == 1


@pytest.mark.asyncio
async def test_failure_rate_uses_assembly_count(svc):
    # 1 assembly recorded, 1 failure → 100%
    svc.record_assembly_latency("u1", 50.0)
    svc.record_failure("u1", FAILURE_EMBEDDING_UNAVAILABLE, "semantic_retrieval")
    result = await svc.get_failure_summary()
    assert result["failure_rate_pct"] == 100.0


@pytest.mark.asyncio
async def test_failure_window_excludes_old_events(svc):
    svc.record_failure("u1", FAILURE_EMBEDDING_UNAVAILABLE, "semantic_retrieval")
    old = svc._failure_events[-1].copy()
    old["ts"] = datetime.utcnow() - timedelta(hours=25)
    svc._failure_events.append(old)

    result = await svc.get_failure_summary(window_hours=24)
    assert result["sample_count"] == 1


# ---------------------------------------------------------------------------
# Embedding dedup (Q5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_embedding_dedup_delegates_to_embedding_service(svc):
    import api.services.embedding_service as es_mod

    original = es_mod.embedding_service
    mock_embed = MagicMock()
    mock_embed.get_dedup_stats.return_value = {"duplicates_prevented": 7, "hash_cache_size": 42}
    es_mod.embedding_service = mock_embed

    result = await svc.get_embedding_dedup_stats()
    assert result["duplicates_prevented"] == 7

    es_mod.embedding_service = original


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_report_keys_present(svc, monkeypatch):
    import api.services.cache_service as cs_mod
    import api.services.embedding_service as es_mod

    cs_mod.cache_service = MagicMock()
    cs_mod.cache_service.get_hit_rate.return_value = {
        "hits": 0,
        "misses": 0,
        "rate": 0.0,
        "total": 0,
    }
    es_mod.embedding_service = MagicMock()
    es_mod.embedding_service.get_dedup_stats.return_value = {
        "duplicates_prevented": 0,
        "hash_cache_size": 0,
    }

    result = await svc.get_full_report()
    expected_keys = {
        "generated_at",
        "window_hours",
        "user_id",
        "token_budget_accuracy",
        "tier_latency",
        "cache_hit_rate",
        "failure_summary",
        "embedding_dedup",
    }
    assert expected_keys.issubset(result.keys())
