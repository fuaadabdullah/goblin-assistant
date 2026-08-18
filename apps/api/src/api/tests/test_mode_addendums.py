from __future__ import annotations

import pytest

from api.config.mode_addendums import (
    CATEGORY_ADDENDUMS,
    MODE_REGISTRY,
    Mode,
    ModeAddendum,
    get_addendum,
    get_mode_addendum,
    list_canonical_modes,
    list_modes,
)

# ── Legacy ModeKey tests (backward compat) ───────────────────────────────


def test_general_assistant_mode_addendum_resolves():
    addendum = get_addendum("GENERAL_ASSISTANT")
    assert "[GENERAL ASSISTANT MODE]" in addendum
    assert "lightweight research" in addendum.lower()
    assert "web_search or lightweight_research" in addendum.lower()


def test_unknown_mode_still_raises_key_error():
    with pytest.raises(KeyError) as exc:
        get_addendum("DOES_NOT_EXIST")
    assert "Valid modes" in str(exc.value)


def test_general_assistant_mode_listed():
    assert "GENERAL_ASSISTANT" in list_modes()


def test_deep_research_mode_addendum_resolves():
    addendum = get_addendum("DEEP_RESEARCH")
    assert "[DEEP RESEARCH MODE" in addendum


def test_deep_research_has_own_addendum_distinct_from_research():
    assert get_addendum("DEEP_RESEARCH") != get_addendum("RESEARCH")


def test_deep_research_mode_listed():
    assert "DEEP_RESEARCH" in list_modes()


def test_research_category_addendum_present():
    addendum = CATEGORY_ADDENDUMS["research"]
    assert "web_search or lightweight_research" in addendum.lower()


def test_finance_category_addendum_present():
    addendum = CATEGORY_ADDENDUMS["finance"]
    assert "web_search or lightweight_research" in addendum.lower()


def test_research_category_addendum_mentions_live_sources():
    addendum = CATEGORY_ADDENDUMS["research"]
    assert "web_search or lightweight_research" in addendum


def test_finance_category_addendum_mentions_live_sources():
    addendum = CATEGORY_ADDENDUMS["finance"]
    assert "web_search or lightweight_research" in addendum


# ── New canonical Mode + ModeAddendum registry tests ─────────────────────


def test_mode_enum_values():
    """All expected modes are present with correct string values."""
    assert Mode.CHAT.value == "chat"
    assert Mode.CODE.value == "code"
    assert Mode.RESEARCH.value == "research"
    assert Mode.EDUCATION.value == "education"
    assert Mode.FINANCE.value == "finance"
    assert Mode.AGENT.value == "agent"


def test_mode_registry_has_all_modes():
    """Every Mode member has a corresponding ModeAddendum in the registry."""
    for mode in Mode:
        assert mode in MODE_REGISTRY, f"Mode.{mode.name} missing from MODE_REGISTRY"


def test_mode_registry_fields():
    """Every ModeAddendum has the expected field structure."""
    for mode, addendum in MODE_REGISTRY.items():
        assert isinstance(addendum, ModeAddendum)
        assert addendum.mode is mode
        assert isinstance(addendum.directive, str) and len(addendum.directive) > 0
        assert isinstance(addendum.tool_bias, list)
        assert isinstance(addendum.output_shape, str) and len(addendum.output_shape) > 0
        assert isinstance(addendum.active, bool)


def test_active_modes_resolve():
    """All active modes resolve without raising."""
    for mode, addendum in MODE_REGISTRY.items():
        if addendum.active:
            result = get_mode_addendum(mode)
            assert result is addendum


def test_inactive_mode_raises_value_error():
    """Finance mode is scaffolded but inactive — must raise ValueError."""
    assert not MODE_REGISTRY[Mode.FINANCE].active
    with pytest.raises(ValueError, match="scaffolded but not active"):
        get_mode_addendum(Mode.FINANCE)


def test_unregistered_mode_raises_value_error():
    """Passing a bogus Mode value raises ValueError."""
    # Construct a valid Mode to verify the registry check.
    # We cannot easily create an unregistered Mode without hacking the enum,
    # so we test the None guard instead.
    with pytest.raises(ValueError, match="unregistered mode"):
        get_mode_addendum(None)  # type: ignore[arg-type]


def test_chat_is_default():
    """CHAT mode is active and the default."""
    addendum = get_mode_addendum(Mode.CHAT)
    assert addendum.active is True
    assert "conversational" in addendum.directive.lower() or "direct" in addendum.directive.lower()


def test_code_mode_has_tool_bias():
    """CODE mode declares sandbox_executor and code_review in tool_bias."""
    addendum = get_mode_addendum(Mode.CODE)
    assert "sandbox_executor" in addendum.tool_bias
    assert "code_review" in addendum.tool_bias


def test_research_mode_has_tool_bias():
    """RESEARCH mode declares web_search and document_retrieval in tool_bias."""
    addendum = get_mode_addendum(Mode.RESEARCH)
    assert "web_search" in addendum.tool_bias
    assert "document_retrieval" in addendum.tool_bias


def test_agent_mode_active():
    """AGENT mode is active with the expected output_shape."""
    addendum = get_mode_addendum(Mode.AGENT)
    assert addendum.active is True
    assert addendum.output_shape == "plan_then_execution_log"


def test_list_canonical_modes():
    """list_canonical_modes returns all Mode values in stable order."""
    modes = list_canonical_modes()
    assert len(modes) == len(Mode)
    assert modes == [m.value for m in Mode]


def test_frozen_dataclass():
    """ModeAddendum is immutable."""
    addendum = get_mode_addendum(Mode.CHAT)
    with pytest.raises(AttributeError):
        addendum.directive = "nope"  # type: ignore[misc]
