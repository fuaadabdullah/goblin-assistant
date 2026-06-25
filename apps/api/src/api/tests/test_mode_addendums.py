from __future__ import annotations

import pytest

from api.config.mode_addendums import get_addendum, list_modes


def test_general_assistant_mode_addendum_resolves():
    addendum = get_addendum("GENERAL_ASSISTANT")
    assert "[GENERAL ASSISTANT MODE]" in addendum
    assert "lightweight research" in addendum.lower()


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
