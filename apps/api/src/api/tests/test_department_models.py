"""Tests for departments/models.py — pure dataclasses, enums, and helpers."""

from __future__ import annotations

import dataclasses

import pytest

from api.departments.models import (
    INTENT_TO_DEPARTMENT,
    DepartmentId,
    DepartmentPolicy,
    DepartmentQualityTier,
    DepartmentSelection,
    DepartmentSpecialization,
    quality_tier_for_complexity,
)

# ── DepartmentId enum ─────────────────────────────────────────────────────────


class TestDepartmentId:
    def test_all_seven_values_exist(self):
        ids = {d.value for d in DepartmentId}
        assert ids == {
            "reasoning",
            "coding",
            "creative",
            "recall",
            "tool_use",
            "research",
            "general",
        }

    def test_is_string_subclass(self):
        assert isinstance(DepartmentId.GENERAL, str)
        assert DepartmentId.GENERAL == "general"

    def test_from_string_value(self):
        assert DepartmentId("reasoning") is DepartmentId.REASONING
        assert DepartmentId("general") is DepartmentId.GENERAL

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            DepartmentId("nonexistent")


# ── DepartmentQualityTier enum ────────────────────────────────────────────────


class TestDepartmentQualityTier:
    def test_all_four_values_exist(self):
        values = {t.value for t in DepartmentQualityTier}
        assert values == {"speed", "balanced", "quality", "economy"}

    def test_is_string_subclass(self):
        assert isinstance(DepartmentQualityTier.BALANCED, str)
        assert DepartmentQualityTier.BALANCED == "balanced"


# ── DepartmentPolicy dataclass ────────────────────────────────────────────────


class TestDepartmentPolicy:
    def _make_policy(self, chain=None):
        return DepartmentPolicy(
            department_id=DepartmentId.GENERAL,
            display_name="General",
            description="General purpose",
            provider_chain=[("openai", "gpt-4o-mini"), ("anthropic", "claude-haiku-4-5-20251001")]
            if chain is None
            else chain,
        )

    def test_construction_with_required_fields(self):
        policy = self._make_policy()
        assert policy.department_id is DepartmentId.GENERAL
        assert policy.display_name == "General"

    def test_defaults(self):
        policy = self._make_policy()
        assert policy.specializations == []
        assert policy.default_tier is DepartmentQualityTier.BALANCED
        assert policy.supports_streaming is True
        assert policy.supports_tools is True
        assert policy.supports_attachments is True
        assert policy.supports_vision is False
        assert policy.max_tokens == 4096
        assert policy.temperature_default == pytest.approx(0.7)

    def test_primary_provider_returns_first_entry(self):
        policy = self._make_policy([("openai", "gpt-4o"), ("anthropic", "claude")])
        assert policy.primary_provider == ("openai", "gpt-4o")

    def test_fallback_providers_returns_rest(self):
        policy = self._make_policy(
            [("openai", "gpt-4o"), ("anthropic", "claude"), ("gemini", "flash")]
        )
        assert policy.fallback_providers == [("anthropic", "claude"), ("gemini", "flash")]

    def test_single_entry_chain_has_empty_fallbacks(self):
        policy = self._make_policy([("openai", "gpt-4o")])
        assert policy.fallback_providers == []

    def test_empty_chain_primary_returns_empty_strings(self):
        policy = self._make_policy([])
        assert policy.primary_provider == ("", "")

    def test_empty_chain_fallback_returns_empty_list(self):
        policy = self._make_policy([])
        assert policy.fallback_providers == []

    def test_frozen_assignment_raises(self):
        policy = self._make_policy()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            policy.display_name = "Changed"  # type: ignore[misc]

    def test_override_defaults(self):
        policy = DepartmentPolicy(
            department_id=DepartmentId.CREATIVE,
            display_name="Creative",
            description="Writing and art",
            provider_chain=[("anthropic", "claude-sonnet-4-6")],
            specializations=[
                DepartmentSpecialization(
                    specialization_id="writing",
                    display_name="Writing",
                    description="Drafting and editorial polish",
                    routing_hints=["drafting", "editing"],
                )
            ],
            supports_vision=True,
            max_tokens=8192,
            temperature_default=0.9,
        )
        assert policy.supports_vision is True
        assert policy.max_tokens == 8192
        assert policy.temperature_default == pytest.approx(0.9)

    def test_to_dict_omits_specializations_by_default(self):
        policy = self._make_policy()
        payload = policy.to_dict()
        assert "specializations" not in payload
        assert payload["department_id"] == "general"
        assert payload["provider_chain"] == [
            ["openai", "gpt-4o-mini"],
            ["anthropic", "claude-haiku-4-5-20251001"],
        ]

    def test_to_dict_can_include_specializations(self):
        policy = DepartmentPolicy(
            department_id=DepartmentId.CODING,
            display_name="Coding",
            description="Code changes",
            provider_chain=[("anthropic", "claude-sonnet-4-20250514")],
            specializations=[
                DepartmentSpecialization(
                    specialization_id="frontend",
                    display_name="Frontend",
                    description="UI work",
                    routing_hints=["react", "css"],
                )
            ],
        )
        payload = policy.to_dict(include_specializations=True)
        assert payload["specializations"] == [
            {
                "specialization_id": "frontend",
                "display_name": "Frontend",
                "description": "UI work",
                "routing_hints": ["react", "css"],
            }
        ]

    def test_round_trip_preserves_specializations(self):
        payload = {
            "department_id": "research",
            "display_name": "Research",
            "description": "Research work",
            "provider_chain": [["gemini", "gemini-2.5-flash-001"]],
            "specializations": [
                {
                    "specialization_id": "legal",
                    "display_name": "Legal",
                    "description": "Regulatory review",
                    "routing_hints": ["policy", "compliance"],
                }
            ],
            "default_tier": "quality",
            "supports_streaming": True,
            "supports_tools": True,
            "supports_attachments": False,
            "supports_vision": False,
            "max_tokens": 8192,
            "temperature_default": 0.5,
        }
        policy = DepartmentPolicy.from_dict(payload)
        assert policy.department_id is DepartmentId.RESEARCH
        assert policy.default_tier is DepartmentQualityTier.QUALITY
        assert policy.specializations == [
            DepartmentSpecialization(
                specialization_id="legal",
                display_name="Legal",
                description="Regulatory review",
                routing_hints=["policy", "compliance"],
            )
        ]
        assert (
            policy.to_dict(include_specializations=True)["specializations"]
            == payload["specializations"]
        )


# ── DepartmentSpecialization dataclass ────────────────────────────────────────


class TestDepartmentSpecialization:
    def test_defaults_are_serializable(self):
        specialization = DepartmentSpecialization(
            specialization_id="frontend",
            display_name="Frontend",
            description="UI work",
        )
        assert specialization.routing_hints == []
        assert specialization.to_dict() == {
            "specialization_id": "frontend",
            "display_name": "Frontend",
            "description": "UI work",
            "routing_hints": [],
        }

    def test_from_dict_round_trip(self):
        payload = {
            "specialization_id": "backend",
            "display_name": "Backend",
            "description": "Server work",
            "routing_hints": ["api", "routes"],
        }
        specialization = DepartmentSpecialization.from_dict(payload)
        assert specialization == DepartmentSpecialization(
            specialization_id="backend",
            display_name="Backend",
            description="Server work",
            routing_hints=["api", "routes"],
        )


# ── DepartmentSelection dataclass ─────────────────────────────────────────────


class TestDepartmentSelection:
    def test_construction_with_required_field_only(self):
        sel = DepartmentSelection(department_id=DepartmentId.CODING)
        assert sel.department_id is DepartmentId.CODING
        assert sel.reason == ""
        assert sel.resolved_provider == ""
        assert sel.resolved_model == ""

    def test_construction_with_all_fields(self):
        sel = DepartmentSelection(
            department_id=DepartmentId.REASONING,
            reason="complex math task",
            resolved_provider="anthropic",
            resolved_model="claude-opus-4-8",
            quality_tier=DepartmentQualityTier.QUALITY,
        )
        assert sel.resolved_provider == "anthropic"
        assert sel.quality_tier is DepartmentQualityTier.QUALITY

    def test_to_dict_returns_only_department_and_reason(self):
        sel = DepartmentSelection(
            department_id=DepartmentId.RESEARCH,
            reason="deep investigation",
            resolved_provider="gemini",
            resolved_model="gemini-pro",
        )
        d = sel.to_dict()
        assert d == {"department": "research", "reason": "deep investigation"}

    def test_to_dict_no_provider_leakage(self):
        sel = DepartmentSelection(
            department_id=DepartmentId.CODING,
            resolved_provider="secret_provider",
            resolved_model="secret_model",
        )
        d = sel.to_dict()
        assert "secret_provider" not in str(d)
        assert "secret_model" not in str(d)
        assert "resolved_provider" not in d
        assert "resolved_model" not in d

    def test_fallback_chain_defaults_to_empty_list(self):
        sel = DepartmentSelection(department_id=DepartmentId.TOOL_USE)
        assert sel.fallback_chain == []

    def test_mutable_unlike_policy(self):
        sel = DepartmentSelection(department_id=DepartmentId.GENERAL)
        sel.resolved_provider = "openai"
        assert sel.resolved_provider == "openai"


# ── INTENT_TO_DEPARTMENT mapping ──────────────────────────────────────────────


class TestIntentToDepartment:
    def test_reasoning_intents_map_correctly(self):
        assert INTENT_TO_DEPARTMENT["reasoning"] is DepartmentId.REASONING
        assert INTENT_TO_DEPARTMENT["logic"] is DepartmentId.REASONING
        assert INTENT_TO_DEPARTMENT["math"] is DepartmentId.REASONING
        assert INTENT_TO_DEPARTMENT["planning"] is DepartmentId.REASONING

    def test_coding_intents_map_correctly(self):
        assert INTENT_TO_DEPARTMENT["coding"] is DepartmentId.CODING
        assert INTENT_TO_DEPARTMENT["debugging"] is DepartmentId.CODING
        assert INTENT_TO_DEPARTMENT["code_review"] is DepartmentId.CODING

    def test_creative_intents_map_correctly(self):
        assert INTENT_TO_DEPARTMENT["creative"] is DepartmentId.CREATIVE
        assert INTENT_TO_DEPARTMENT["writing"] is DepartmentId.CREATIVE
        assert INTENT_TO_DEPARTMENT["brainstorming"] is DepartmentId.CREATIVE

    def test_recall_intents_map_correctly(self):
        assert INTENT_TO_DEPARTMENT["recall"] is DepartmentId.RECALL
        assert INTENT_TO_DEPARTMENT["memory"] is DepartmentId.RECALL
        assert INTENT_TO_DEPARTMENT["retrieval"] is DepartmentId.RECALL

    def test_tool_use_intents_map_correctly(self):
        assert INTENT_TO_DEPARTMENT["tool_use"] is DepartmentId.TOOL_USE
        assert INTENT_TO_DEPARTMENT["function_calling"] is DepartmentId.TOOL_USE
        assert INTENT_TO_DEPARTMENT["automation"] is DepartmentId.TOOL_USE

    def test_research_intents_map_correctly(self):
        assert INTENT_TO_DEPARTMENT["research"] is DepartmentId.RESEARCH
        assert INTENT_TO_DEPARTMENT["deep_research"] is DepartmentId.RESEARCH
        assert INTENT_TO_DEPARTMENT["synthesis"] is DepartmentId.RESEARCH

    def test_unknown_intent_not_in_map(self):
        assert "unknown_intent" not in INTENT_TO_DEPARTMENT
        assert "chat" not in INTENT_TO_DEPARTMENT

    def test_all_values_are_department_ids(self):
        for _key, val in INTENT_TO_DEPARTMENT.items():
            assert isinstance(val, DepartmentId)


# ── quality_tier_for_complexity ───────────────────────────────────────────────


class TestQualityTierForComplexity:
    def test_zero_maps_to_speed(self):
        assert quality_tier_for_complexity(0.0) is DepartmentQualityTier.SPEED

    def test_boundary_0_2_maps_to_speed(self):
        assert quality_tier_for_complexity(0.2) is DepartmentQualityTier.SPEED

    def test_just_above_0_2_maps_to_economy(self):
        assert quality_tier_for_complexity(0.21) is DepartmentQualityTier.ECONOMY

    def test_boundary_0_4_maps_to_economy(self):
        assert quality_tier_for_complexity(0.4) is DepartmentQualityTier.ECONOMY

    def test_just_above_0_4_maps_to_balanced(self):
        assert quality_tier_for_complexity(0.41) is DepartmentQualityTier.BALANCED

    def test_boundary_0_7_maps_to_balanced(self):
        assert quality_tier_for_complexity(0.7) is DepartmentQualityTier.BALANCED

    def test_just_above_0_7_maps_to_quality(self):
        assert quality_tier_for_complexity(0.71) is DepartmentQualityTier.QUALITY

    def test_one_maps_to_quality(self):
        assert quality_tier_for_complexity(1.0) is DepartmentQualityTier.QUALITY

    def test_midpoint_0_5_maps_to_balanced(self):
        assert quality_tier_for_complexity(0.5) is DepartmentQualityTier.BALANCED

    def test_midpoint_0_1_maps_to_speed(self):
        assert quality_tier_for_complexity(0.1) is DepartmentQualityTier.SPEED

    def test_midpoint_0_9_maps_to_quality(self):
        assert quality_tier_for_complexity(0.9) is DepartmentQualityTier.QUALITY
