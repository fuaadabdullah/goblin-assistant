"""Tests for FeatureExtractor — pure routing logic with no external dependencies."""

from __future__ import annotations

import pytest

from api.routing.feature_extractor import FeatureExtractor


@pytest.fixture
def extractor() -> FeatureExtractor:
    return FeatureExtractor()


# ---------------------------------------------------------------------------
# extract_request — prompt length bucketing
# ---------------------------------------------------------------------------


class TestPromptLengthBuckets:
    def test_short_prompt_is_bucket_0(self, extractor):
        features = extractor.extract_request("hi", "chat", [])
        assert features.prompt_length_bucket == 0

    def test_boundary_399_chars_is_bucket_0(self, extractor):
        features = extractor.extract_request("x" * 399, "chat", [])
        assert features.prompt_length_bucket == 0

    def test_boundary_400_chars_is_bucket_1(self, extractor):
        features = extractor.extract_request("x" * 400, "chat", [])
        assert features.prompt_length_bucket == 1

    def test_boundary_1599_chars_is_bucket_1(self, extractor):
        features = extractor.extract_request("x" * 1599, "chat", [])
        assert features.prompt_length_bucket == 1

    def test_boundary_1600_chars_is_bucket_2(self, extractor):
        features = extractor.extract_request("x" * 1600, "chat", [])
        assert features.prompt_length_bucket == 2

    def test_boundary_6400_chars_is_bucket_3(self, extractor):
        features = extractor.extract_request("x" * 6400, "chat", [])
        assert features.prompt_length_bucket == 3


# ---------------------------------------------------------------------------
# extract_request — complexity scoring
# ---------------------------------------------------------------------------


class TestComplexityScoring:
    def test_plain_statement_has_low_complexity(self, extractor):
        features = extractor.extract_request("The sky is blue.", "chat", [])
        assert features.complexity_score < 0.2

    def test_question_marks_raise_complexity(self, extractor):
        features = extractor.extract_request("Why? How? What? When?", "chat", [])
        assert features.complexity_score > 0.1

    def test_code_blocks_raise_complexity(self, extractor):
        prompt = "```python\nfor i in range(10):\n    pass\n```\n" * 2
        features = extractor.extract_request(prompt, "code", [])
        assert features.complexity_score > 0.1

    def test_complexity_keywords_raise_score(self, extractor):
        features = extractor.extract_request(
            "Can you explain and analyse the trade-off?", "chat", []
        )
        assert features.complexity_score > 0.15

    def test_depth_keywords_raise_score(self, extractor):
        features = extractor.extract_request(
            "Please explain this step by step in detail.", "chat", []
        )
        assert features.complexity_score > 0.15

    def test_complexity_score_clamped_to_one(self, extractor):
        # Combine every complexity signal
        prompt = (
            "Why? " * 10
            + "``` " * 4
            + "explain analyse compare trade-off step by step in detail comprehensive "
            + "x" * 4000
        )
        features = extractor.extract_request(prompt, "code", [])
        assert features.complexity_score <= 1.0


# ---------------------------------------------------------------------------
# extract_request — retrieval / tool / latency probability
# ---------------------------------------------------------------------------


class TestSignalProbabilities:
    def test_retrieval_keywords_detected(self, extractor):
        features = extractor.extract_request("Can you find and search for AAPL?", "chat", [])
        assert features.retrieval_probability > 0.0

    def test_tool_keywords_detected(self, extractor):
        features = extractor.extract_request("Please schedule and send the email.", "chat", [])
        assert features.tool_probability > 0.0

    def test_latency_keyword_sets_sensitivity_to_one(self, extractor):
        features = extractor.extract_request("Quick answer please, tldr version.", "chat", [])
        assert features.latency_sensitivity == 1.0

    def test_no_special_keywords_leaves_signals_at_zero(self, extractor):
        features = extractor.extract_request("The meaning of life is 42.", "chat", [])
        assert features.retrieval_probability == 0.0
        assert features.tool_probability == 0.0
        assert features.latency_sensitivity == 0.0

    def test_retrieval_probability_clamped_to_one(self, extractor):
        keywords = (
            "find search look up lookup who is what is when did where is tell me about what are"
        )
        features = extractor.extract_request(keywords, "chat", [])
        assert features.retrieval_probability <= 1.0


# ---------------------------------------------------------------------------
# extract_request — conversation turn cap
# ---------------------------------------------------------------------------


class TestConversationTurn:
    def test_turn_count_reflects_history_length(self, extractor):
        history = [{"role": "user", "content": "hi"}] * 5
        features = extractor.extract_request("hello", "chat", history)
        assert features.conversation_turn == 5

    def test_turn_count_capped_at_ten(self, extractor):
        history = [{"role": "user", "content": "msg"}] * 25
        features = extractor.extract_request("hello", "chat", history)
        assert features.conversation_turn == 10

    def test_empty_history_gives_turn_zero(self, extractor):
        features = extractor.extract_request("hello", "chat", [])
        assert features.conversation_turn == 0


# ---------------------------------------------------------------------------
# extract_request — intent passthrough
# ---------------------------------------------------------------------------


class TestIntentPassthrough:
    def test_intent_label_and_confidence_are_preserved(self, extractor):
        features = extractor.extract_request(
            "help me write code",
            "code",
            [],
            intent_label="coding",
            intent_confidence=0.87,
        )
        assert features.intent_label == "coding"
        assert features.intent_confidence == pytest.approx(0.87, abs=1e-4)

    def test_task_type_is_stored_as_given(self, extractor):
        features = extractor.extract_request("do research", "research", [])
        assert features.task_type == "research"


# ---------------------------------------------------------------------------
# extract_providers — normalisation
# ---------------------------------------------------------------------------


class TestExtractProviders:
    def test_empty_candidates_returns_empty(self, extractor):
        result = extractor.extract_providers([], {}, {})
        assert result == {}

    def test_single_candidate_gets_full_latency_normalisation(self, extractor):
        snapshot = {"only": {"ewma_latency_ms": 300.0, "success_rate": 0.9}}
        result = extractor.extract_providers(["only"], {}, snapshot)
        assert result["only"].norm_latency == pytest.approx(1.0)
        assert result["only"].success_rate == pytest.approx(0.9)

    def test_fastest_provider_has_lowest_norm_latency(self, extractor):
        snapshot = {
            "fast": {"ewma_latency_ms": 200.0, "success_rate": 0.9},
            "slow": {"ewma_latency_ms": 2000.0, "success_rate": 0.9},
        }
        result = extractor.extract_providers(["fast", "slow"], {}, snapshot)
        assert result["fast"].norm_latency < result["slow"].norm_latency
        assert result["slow"].norm_latency == pytest.approx(1.0)

    def test_cheapest_provider_has_lowest_norm_cost(self, extractor):
        costs = {"cheap": (0.001, 0.002), "pricey": (0.01, 0.02)}
        result = extractor.extract_providers(["cheap", "pricey"], costs, {})
        assert result["cheap"].norm_cost < result["pricey"].norm_cost
        assert result["pricey"].norm_cost == pytest.approx(1.0)

    def test_missing_registry_stats_use_defaults(self, extractor):
        result = extractor.extract_providers(["unknown"], {}, {})
        pf = result["unknown"]
        assert pf.success_rate == pytest.approx(0.5)
        assert pf.norm_latency == pytest.approx(1.0)
        assert pf.is_healthy is True

    def test_health_availability_propagated(self, extractor):
        health = {"healthy": True, "degraded": False}
        result = extractor.extract_providers(
            ["healthy", "degraded"], {}, {}, health_availability=health
        )
        assert result["healthy"].is_healthy is True
        assert result["degraded"].is_healthy is False

    def test_success_rate_clamped_between_zero_and_one(self, extractor):
        snapshot = {
            "over": {"success_rate": 1.5},
            "under": {"success_rate": -0.2},
        }
        result = extractor.extract_providers(["over", "under"], {}, snapshot)
        assert result["over"].success_rate == pytest.approx(1.0)
        assert result["under"].success_rate == pytest.approx(0.0)

    def test_all_zero_costs_produces_zero_norm_cost(self, extractor):
        result = extractor.extract_providers(["a", "b"], {"a": (0.0, 0.0), "b": (0.0, 0.0)}, {})
        assert result["a"].norm_cost == pytest.approx(0.0)
        assert result["b"].norm_cost == pytest.approx(0.0)
