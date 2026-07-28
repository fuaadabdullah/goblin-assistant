from __future__ import annotations

import pytest

from api.config.mode_addendums import CATEGORY_ADDENDUMS, get_addendum, list_modes


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


def test_research_category_addendum_mentions_live_sources():
    addendum = CATEGORY_ADDENDUMS["research"]
    assert "web_search or lightweight_research" in addendum


def test_finance_category_addendum_mentions_live_sources():
    addendum = CATEGORY_ADDENDUMS["finance"]
    assert "web_search or lightweight_research" in addendum
