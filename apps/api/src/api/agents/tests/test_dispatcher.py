"""Tests for the agent archetype registry and intent dispatcher."""

import pytest

from api.agents.archetypes import (
    ARCHETYPE_REGISTRY,
    AgentArchetypeId,
)
from api.agents.dispatcher import _SPECIALIST_CONFIDENCE_THRESHOLD, IntentDispatcher
from api.routing.intent_models import IntentLabel, IntentResult


def _intent(label: IntentLabel, confidence: float = 0.8, method: str = "keyword") -> IntentResult:
    return IntentResult(label=label, confidence=confidence, method=method)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestArchetypeRegistry:
    def test_all_archetypes_present(self):
        ids = {a.archetype_id for a in ARCHETYPE_REGISTRY.list_all()}
        assert ids == set(AgentArchetypeId)

    def test_build_order_is_sorted(self):
        orders = [a.build_order for a in ARCHETYPE_REGISTRY.list_all()]
        assert orders == sorted(orders)

    def test_general_assistant_is_first(self):
        first = ARCHETYPE_REGISTRY.list_all()[0]
        assert first.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT

    def test_forge_tm_is_last(self):
        last = ARCHETYPE_REGISTRY.list_all()[-1]
        assert last.archetype_id == AgentArchetypeId.FORGE_TM

    def test_forge_tm_not_available(self):
        forge = ARCHETYPE_REGISTRY.get(AgentArchetypeId.FORGE_TM)
        assert not forge.is_available

    def test_list_available_excludes_unavailable(self):
        available_ids = {a.archetype_id for a in ARCHETYPE_REGISTRY.list_available()}
        assert AgentArchetypeId.FORGE_TM not in available_ids

    def test_resolve_coding_intent_to_code_review(self):
        archetype = ARCHETYPE_REGISTRY.resolve_intent(IntentLabel.CODING)
        assert archetype.archetype_id == AgentArchetypeId.CODE_REVIEW

    def test_resolve_research_intent_to_deep_research(self):
        archetype = ARCHETYPE_REGISTRY.resolve_intent(IntentLabel.RESEARCH)
        assert archetype.archetype_id == AgentArchetypeId.DEEP_RESEARCH

    def test_resolve_finance_intent_to_forge_tm(self):
        archetype = ARCHETYPE_REGISTRY.resolve_intent(IntentLabel.FINANCE)
        # ForgeTM owns FINANCE even though it's unavailable
        assert archetype.archetype_id == AgentArchetypeId.FORGE_TM

    def test_to_dict_shape(self):
        d = ARCHETYPE_REGISTRY.get(AgentArchetypeId.GENERAL_ASSISTANT).to_dict()
        assert "archetype_id" in d
        assert "display_name" in d
        assert "primary_intents" in d
        assert "departments" in d
        assert "build_order" in d
        assert "is_available" in d


# ---------------------------------------------------------------------------
# Dispatcher — happy paths
# ---------------------------------------------------------------------------


class TestIntentDispatcher:
    @pytest.fixture
    def dispatcher(self) -> IntentDispatcher:
        return IntentDispatcher()

    def test_coding_routes_to_code_review(self, dispatcher):
        sel = dispatcher.dispatch(_intent(IntentLabel.CODING))
        assert sel.archetype.archetype_id == AgentArchetypeId.CODE_REVIEW
        assert not sel.fell_back

    def test_research_routes_to_deep_research(self, dispatcher):
        sel = dispatcher.dispatch(_intent(IntentLabel.RESEARCH))
        assert sel.archetype.archetype_id == AgentArchetypeId.DEEP_RESEARCH
        assert not sel.fell_back

    def test_creative_routes_to_general_assistant(self, dispatcher):
        sel = dispatcher.dispatch(_intent(IntentLabel.CREATIVE))
        assert sel.archetype.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT
        assert not sel.fell_back

    def test_business_routes_to_general_assistant(self, dispatcher):
        sel = dispatcher.dispatch(_intent(IntentLabel.BUSINESS))
        assert sel.archetype.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT
        assert not sel.fell_back

    def test_reasoning_routes_to_general_assistant(self, dispatcher):
        sel = dispatcher.dispatch(_intent(IntentLabel.REASONING))
        assert sel.archetype.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT
        assert not sel.fell_back

    def test_agent_task_routes_to_general_assistant(self, dispatcher):
        sel = dispatcher.dispatch(_intent(IntentLabel.AGENT_TASK))
        assert sel.archetype.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT
        assert not sel.fell_back

    # ---------------------------------------------------------------------------
    # Fallback: unavailable archetype
    # ---------------------------------------------------------------------------

    def test_finance_falls_back_because_forge_tm_unavailable(self, dispatcher):
        sel = dispatcher.dispatch(_intent(IntentLabel.FINANCE, confidence=0.9))
        assert sel.archetype.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT
        assert sel.fell_back
        assert "archetype_unavailable" in sel.fallback_reason

    # ---------------------------------------------------------------------------
    # Fallback: low confidence
    # ---------------------------------------------------------------------------

    def test_low_confidence_research_falls_back(self, dispatcher):
        low_conf = _SPECIALIST_CONFIDENCE_THRESHOLD - 0.01
        sel = dispatcher.dispatch(_intent(IntentLabel.RESEARCH, confidence=low_conf))
        assert sel.archetype.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT
        assert sel.fell_back
        assert "low_confidence" in sel.fallback_reason

    def test_threshold_confidence_does_not_fall_back(self, dispatcher):
        sel = dispatcher.dispatch(
            _intent(IntentLabel.RESEARCH, confidence=_SPECIALIST_CONFIDENCE_THRESHOLD)
        )
        assert sel.archetype.archetype_id == AgentArchetypeId.DEEP_RESEARCH
        assert not sel.fell_back

    def test_low_confidence_on_general_does_not_fall_back(self, dispatcher):
        # General-assistant intents don't fall back even at low confidence.
        sel = dispatcher.dispatch(_intent(IntentLabel.CREATIVE, confidence=0.1))
        assert sel.archetype.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT
        assert not sel.fell_back

    # ---------------------------------------------------------------------------
    # Convenience: dispatch_label
    # ---------------------------------------------------------------------------

    def test_dispatch_label_convenience(self, dispatcher):
        sel = dispatcher.dispatch_label(IntentLabel.RESEARCH)
        assert sel.archetype.archetype_id == AgentArchetypeId.DEEP_RESEARCH

    def test_to_dict_includes_all_fields(self, dispatcher):
        sel = dispatcher.dispatch(_intent(IntentLabel.CODING))
        d = sel.to_dict()
        assert d["archetype_id"] == "code_review"
        assert d["intent_label"] == "coding"
        assert "intent_confidence" in d
        assert "fell_back" in d
