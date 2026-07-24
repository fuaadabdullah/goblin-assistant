"""Tests for the tone addendum registry and ToneMode enum."""

from __future__ import annotations

from api.config.tone_addendums import (
    ToneMode,
    get_tone_addendum,
    list_tones,
)


def test_tone_mode_is_string_enum():
    # ToneMode values are real strings (this is what makes them serialize
    # cleanly through OpenAPI into the generated SDK types).
    assert ToneMode.DEFAULT == "DEFAULT"
    assert isinstance(ToneMode.FORMAL, str)
    assert ToneMode.FORMAL.value == "FORMAL"


def test_default_tone_returns_empty_string():
    assert get_tone_addendum(ToneMode.DEFAULT) == ""
    assert get_tone_addendum(None) == ""


def test_each_tone_returns_distinct_addendum():
    addenda = {t: get_tone_addendum(t) for t in ToneMode}
    # DEFAULT must be empty so it doesn't pollute the prompt when omitted.
    assert addenda[ToneMode.DEFAULT] == ""
    # Every non-default tone produces a non-empty addendum.
    for tone, addendum in addenda.items():
        if tone == ToneMode.DEFAULT:
            continue
        assert addendum.strip(), f"tone {tone} produced empty addendum"
        # Every addendum declares its own tag so the model can self-verify.
        assert f"[TONE: {tone.value}]" in addendum


def test_string_input_is_case_insensitive():
    assert get_tone_addendum("formal") == get_tone_addendum(ToneMode.FORMAL)
    assert get_tone_addendum("  TECHNICAL  ") == get_tone_addendum(ToneMode.TECHNICAL)


def test_unknown_tone_returns_empty_string_not_raises():
    # Tone is optional — unknown values must not crash the request path.
    assert get_tone_addendum("not-a-real-tone") == ""
    assert get_tone_addendum("") == ""


def test_list_tones_returns_all_values():
    listed = list_tones()
    assert "DEFAULT" in listed
    assert "FORMAL" in listed
    assert "TECHNICAL" in listed
    # Stable order: DEFAULT first.
    assert listed[0] == "DEFAULT"
    # Every enum member is represented.
    assert set(listed) == {t.value for t in ToneMode}


def test_technical_tone_omits_introductory_framing():
    addendum = get_tone_addendum(ToneMode.TECHNICAL)
    assert "engineering audience" in addendum.lower()
    assert "code, file paths" in addendum.lower()


def test_executive_tone_leads_with_recommendation():
    addendum = get_tone_addendum(ToneMode.EXECUTIVE)
    assert "first sentence" in addendum.lower()
    assert "decision" in addendum.lower()


def test_casual_tone_allows_contractions():
    addendum = get_tone_addendum(ToneMode.CASUAL)
    assert "contractions" in addendum.lower()
