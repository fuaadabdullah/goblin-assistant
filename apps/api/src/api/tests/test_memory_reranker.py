"""Tests for MemoryReranker — usefulness scoring over retrieved memory items."""

from datetime import datetime, timedelta, timezone

from api.services.memory_reranker import (
    _SOURCE_TYPE_WEIGHT,
    _recency_factor,
    memory_reranker,
)

# ── _recency_factor unit tests ────────────────────────────────────────────────


class TestRecencyFactor:
    def test_brand_new_item_scores_near_one(self):
        now = datetime.now(timezone.utc)
        score = _recency_factor(now)
        assert score > 0.99

    def test_sixty_day_old_item_scores_near_half(self):
        old = datetime.now(timezone.utc) - timedelta(days=60)
        score = _recency_factor(old)
        # exp(-0.012 * 60) ≈ 0.487
        assert 0.45 < score < 0.55

    def test_one_eighty_day_old_item_scores_low(self):
        very_old = datetime.now(timezone.utc) - timedelta(days=180)
        score = _recency_factor(very_old)
        # exp(-0.012 * 180) ≈ 0.115
        assert score < 0.15

    def test_none_created_at_returns_neutral(self):
        assert _recency_factor(None) == 0.5

    def test_iso_string_parsed_correctly(self):
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        score = _recency_factor(recent)
        assert score > 0.99

    def test_iso_string_with_z_suffix(self):
        # Produce a bare Z-suffix string (no +00:00 offset) as some backends emit
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        score = _recency_factor(recent)
        assert score > 0.99

    def test_recent_beats_old_for_same_type(self):
        new = datetime.now(timezone.utc) - timedelta(days=1)
        old = datetime.now(timezone.utc) - timedelta(days=120)
        assert _recency_factor(new) > _recency_factor(old)


# ── MemoryReranker.rerank unit tests ──────────────────────────────────────────


def _item(source_type="memory", score=0.8, days_old=0, id_="x"):
    return {
        "id": id_,
        "content": f"item {id_}",
        "source_type": source_type,
        "score": score,
        "created_at": datetime.now(timezone.utc) - timedelta(days=days_old),
    }


class TestMemoryRerankerRerank:
    def test_empty_input_returns_empty(self):
        result = memory_reranker.rerank([], query="anything")
        assert result == []

    def test_single_item_returned_unchanged_content(self):
        item = _item()
        result = memory_reranker.rerank([item], query="q")
        assert len(result) == 1
        assert result[0]["content"] == item["content"]

    def test_rerank_score_added_to_each_item(self):
        items = [_item("memory", 0.7), _item("summary", 0.6)]
        result = memory_reranker.rerank(items, query="q")
        assert all("rerank_score" in r for r in result)

    def test_sorted_descending_by_rerank_score(self):
        items = [_item("ephemeral", 0.9, id_="low"), _item("memory", 0.5, id_="high")]
        result = memory_reranker.rerank(items, query="q")
        scores = [r["rerank_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_memory_type_beats_ephemeral_at_equal_similarity(self):
        memory_item = _item("memory", score=0.7, id_="mem")
        ephemeral_item = _item("ephemeral", score=0.7, id_="eph")
        result = memory_reranker.rerank([ephemeral_item, memory_item], query="q")
        assert result[0]["id"] == "mem"

    def test_recent_item_beats_stale_at_equal_similarity_and_type(self):
        fresh = _item("message", score=0.7, days_old=1, id_="fresh")
        stale = _item("message", score=0.7, days_old=150, id_="stale")
        result = memory_reranker.rerank([stale, fresh], query="q")
        assert result[0]["id"] == "fresh"

    def test_high_similarity_memory_beats_low_similarity_memory(self):
        strong = _item("memory", score=0.95, id_="strong")
        weak = _item("memory", score=0.2, id_="weak")
        result = memory_reranker.rerank([weak, strong], query="q")
        assert result[0]["id"] == "strong"

    def test_top_k_limits_output(self):
        items = [_item(id_=str(i)) for i in range(8)]
        result = memory_reranker.rerank(items, query="q", top_k=3)
        assert len(result) == 3

    def test_top_k_none_returns_all(self):
        items = [_item(id_=str(i)) for i in range(5)]
        result = memory_reranker.rerank(items, query="q", top_k=None)
        assert len(result) == 5

    def test_unknown_source_type_uses_default_weight(self):
        item = _item("exotic_type", score=0.5, id_="exotic")
        result = memory_reranker.rerank([item], query="q")
        assert len(result) == 1
        # Should not raise — unknown types get default weight (0.5)
        assert result[0]["rerank_score"] > 0

    def test_low_confidence_memory_does_not_outrank_strong_memory(self):
        strong = {
            **_item("memory", score=0.95, id_="strong"),
            "confidence": 0.95,
            "importance": 0.9,
            "confidence_band": "strong_stable_memory",
        }
        weak = {
            **_item("memory", score=0.99, id_="weak"),
            "confidence": 0.25,
            "importance": 0.95,
            "confidence_band": "do_not_use_by_default",
        }

        result = memory_reranker.rerank([weak, strong], query="q")

        assert result[0]["id"] == "strong"

    def test_direct_correction_can_override_with_recent_signal(self):
        strong = {
            **_item("memory", score=0.6, id_="baseline"),
            "confidence": 0.88,
            "importance": 0.8,
            "confidence_band": "likely_true_usable",
        }
        correction = {
            **_item("memory", score=0.7, id_="correction"),
            "confidence": 0.58,
            "importance": 0.7,
            "confidence_band": "weak_needs_verification",
            "direct_correction": True,
        }

        result = memory_reranker.rerank([strong, correction], query="q")

        assert result[0]["id"] == "correction"

    def test_item_without_created_at_handled_gracefully(self):
        item = {"id": "no_ts", "content": "x", "source_type": "memory", "score": 0.8}
        result = memory_reranker.rerank([item], query="q")
        assert len(result) == 1
        assert result[0]["rerank_score"] > 0

    def test_rerank_score_within_valid_range(self):
        items = [_item(t, 0.7) for t in _SOURCE_TYPE_WEIGHT]
        result = memory_reranker.rerank(items, query="q")
        for r in result:
            assert 0.0 <= r["rerank_score"] <= 1.0

    def test_original_item_keys_preserved(self):
        item = _item()
        item["custom_key"] = "custom_value"
        result = memory_reranker.rerank([item], query="q")
        assert result[0]["custom_key"] == "custom_value"


# ── Source type ordering ──────────────────────────────────────────────────────


class TestSourceTypeOrdering:
    """Verify the type weight hierarchy holds for items with equal similarity and recency."""

    def _same_age_item(self, source_type, id_):
        # All items created 5 days ago, same cosine score — only type weight differs
        return _item(source_type, score=0.7, days_old=5, id_=id_)

    def test_memory_ranks_above_message(self):
        items = [
            self._same_age_item("message", "msg"),
            self._same_age_item("memory", "mem"),
        ]
        result = memory_reranker.rerank(items, query="q")
        assert result[0]["id"] == "mem"

    def test_summary_ranks_above_task(self):
        items = [
            self._same_age_item("task", "task"),
            self._same_age_item("summary", "sum"),
        ]
        result = memory_reranker.rerank(items, query="q")
        assert result[0]["id"] == "sum"

    def test_ephemeral_ranks_last(self):
        items = [
            self._same_age_item("ephemeral", "eph"),
            self._same_age_item("message", "msg"),
            self._same_age_item("task", "task"),
        ]
        result = memory_reranker.rerank(items, query="q")
        assert result[-1]["id"] == "eph"
