"""Tests for routing/policy_rules.py — declarative PolicyEngine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api.routing.policy_rules import PolicyDecision, PolicyEngine, PolicyRule


def _features(**overrides):
    defaults = dict(
        intent_label="chat",
        task_type="chat",
        complexity_score=0.5,
        prompt_length_bucket=1,
        latency_sensitivity=0.0,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


# ── PolicyRule.matches ──────────────────────────────────────────────────────


class TestPolicyRuleMatches:
    def test_matches_single_intent(self):
        rule = PolicyRule(id="r1", description="", when={"intent": "coding"}, action={})
        assert rule.matches(_features(intent_label="coding"), {}) is True
        assert rule.matches(_features(intent_label="chat"), {}) is False

    def test_matches_intent_list(self):
        rule = PolicyRule(
            id="r1", description="", when={"intent": ["coding", "research"]}, action={}
        )
        assert rule.matches(_features(intent_label="research"), {}) is True
        assert rule.matches(_features(intent_label="creative"), {}) is False

    def test_complexity_min_max(self):
        rule = PolicyRule(
            id="r1", description="", when={"complexity_min": 0.5, "complexity_max": 0.9}, action={}
        )
        assert rule.matches(_features(complexity_score=0.7), {}) is True
        assert rule.matches(_features(complexity_score=0.3), {}) is False
        assert rule.matches(_features(complexity_score=0.95), {}) is False

    def test_prompt_length_bucket_bounds(self):
        rule = PolicyRule(id="r1", description="", when={"prompt_length_bucket_min": 3}, action={})
        assert rule.matches(_features(prompt_length_bucket=3), {}) is True
        assert rule.matches(_features(prompt_length_bucket=2), {}) is False

    def test_metadata_condition(self):
        rule = PolicyRule(
            id="r1", description="", when={"metadata": {"confidential": True}}, action={}
        )
        assert rule.matches(_features(), {"confidential": True}) is True
        assert rule.matches(_features(), {"confidential": False}) is False
        assert rule.matches(_features(), {}) is False

    def test_multiple_conditions_are_and(self):
        rule = PolicyRule(
            id="r1",
            description="",
            when={"intent": "coding", "complexity_min": 0.8},
            action={},
        )
        assert rule.matches(_features(intent_label="coding", complexity_score=0.9), {}) is True
        assert rule.matches(_features(intent_label="coding", complexity_score=0.2), {}) is False

    def test_unknown_condition_key_is_ignored_not_fatal(self):
        rule = PolicyRule(id="r1", description="", when={"bogus_key": "x"}, action={})
        assert rule.matches(_features(), {}) is True


# ── PolicyDecision ───────────────────────────────────────────────────────────


class TestPolicyDecision:
    def test_no_restriction_returns_candidates_unchanged(self):
        decision = PolicyDecision()
        assert decision.apply_restriction(["a", "b"]) == ["a", "b"]

    def test_restriction_filters_candidates(self):
        decision = PolicyDecision(restrict_to={"a"})
        assert decision.apply_restriction(["a", "b"]) == ["a"]

    def test_restriction_matching_nothing_falls_back_to_full_set(self):
        decision = PolicyDecision(restrict_to={"z"})
        assert decision.apply_restriction(["a", "b"]) == ["a", "b"]

    def test_boosts_apply_additively(self):
        decision = PolicyDecision(boosts={"a": 0.2})
        scores = {"a": 0.5, "b": 0.5}
        decision.apply_boosts(scores)
        assert scores["a"] == pytest.approx(0.7)
        assert scores["b"] == pytest.approx(0.5)

    def test_boost_for_absent_provider_is_noop(self):
        decision = PolicyDecision(boosts={"missing": 0.2})
        scores = {"a": 0.5}
        decision.apply_boosts(scores)
        assert scores == {"a": 0.5}


# ── PolicyEngine ─────────────────────────────────────────────────────────────


def _write_policies_toml(path, content: str):
    path.write_text(content)
    return path


class TestPolicyEngine:
    def test_no_config_file_yields_no_rules(self, tmp_path):
        engine = PolicyEngine()
        with patch("api.routing.policy_rules._POLICIES_PATH", tmp_path / "missing.toml"):
            decision = engine.evaluate(_features(), ["a", "b"])
        assert decision.matched_rules == []
        assert decision.restrict_to is None
        assert decision.boosts == {}

    def test_boost_providers_rule_fires(self, tmp_path):
        toml_path = _write_policies_toml(
            tmp_path / "policies.toml",
            """
            [[rules]]
            id = "coding_boost"
            when = { intent = "coding" }
            action = { boost_providers = { anthropic = 0.1 } }
            """,
        )
        engine = PolicyEngine()
        mock_tier_router = MagicMock()
        with (
            patch("api.routing.policy_rules._POLICIES_PATH", toml_path),
            patch.dict(
                "sys.modules",
                {"api.routing.policy_engine": MagicMock(tier_router=mock_tier_router)},
            ),
        ):
            decision = engine.evaluate(_features(intent_label="coding"), ["openai", "anthropic"])
        assert decision.matched_rules == ["coding_boost"]
        assert decision.boosts == {"anthropic": 0.1}

    def test_restrict_tier_rule_intersects_with_candidates(self, tmp_path):
        toml_path = _write_policies_toml(
            tmp_path / "policies.toml",
            """
            [[rules]]
            id = "confidential"
            when = { metadata = { confidential = true } }
            action = { restrict_tier = "local" }
            """,
        )
        engine = PolicyEngine()
        mock_tier_router = MagicMock()
        mock_tier_router.providers_for_tier.return_value = ["ollama_local", "gcp_vm"]
        with (
            patch("api.routing.policy_rules._POLICIES_PATH", toml_path),
            patch.dict(
                "sys.modules",
                {"api.routing.policy_engine": MagicMock(tier_router=mock_tier_router)},
            ),
        ):
            decision = engine.evaluate(
                _features(), ["openai", "ollama_local"], metadata={"confidential": True}
            )
        assert decision.matched_rules == ["confidential"]
        assert decision.apply_restriction(["openai", "ollama_local"]) == ["ollama_local"]

    def test_rule_that_does_not_match_has_no_effect(self, tmp_path):
        toml_path = _write_policies_toml(
            tmp_path / "policies.toml",
            """
            [[rules]]
            id = "coding_boost"
            when = { intent = "coding" }
            action = { boost_providers = { anthropic = 0.1 } }
            """,
        )
        engine = PolicyEngine()
        with patch("api.routing.policy_rules._POLICIES_PATH", toml_path):
            decision = engine.evaluate(_features(intent_label="chat"), ["openai", "anthropic"])
        assert decision.matched_rules == []
        assert decision.boosts == {}

    def test_reload_picks_up_file_changes(self, tmp_path):
        toml_path = tmp_path / "policies.toml"
        toml_path.write_text(
            """
            [[rules]]
            id = "r1"
            when = { intent = "coding" }
            action = { boost_providers = { anthropic = 0.1 } }
            """
        )
        engine = PolicyEngine()
        with patch("api.routing.policy_rules._POLICIES_PATH", toml_path):
            engine.evaluate(_features(intent_label="coding"), ["anthropic"])
            assert len(engine._rules) == 1

            toml_path.write_text(
                """
                [[rules]]
                id = "r1"
                when = { intent = "coding" }
                action = { boost_providers = { anthropic = 0.1 } }

                [[rules]]
                id = "r2"
                when = { intent = "chat" }
                action = { boost_providers = { openai = 0.1 } }
                """
            )
            engine.reload()
            assert len(engine._rules) == 2

    def test_real_config_file_parses(self):
        """Sanity check: the shipped config/routing_policies.toml is valid and loadable."""
        engine = PolicyEngine()
        decision = engine.evaluate(_features(), ["openai", "anthropic", "gemini"])
        assert isinstance(decision, PolicyDecision)
        assert engine._rules  # the shipped file defines at least one rule
