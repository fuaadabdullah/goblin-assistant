"""Tests for the canonical system-prompt composer.

These tests pin down the composition order, which is the whole point of
the prompt_composer module. If you reorder the steps in
`compose_system_prompt`, several of these will fail and force you to
revisit every chat endpoint that depends on the order.
"""

from __future__ import annotations

import pytest

from api.config import tone_addendums
from api.config.prompt_composer import compose_system_prompt
from api.config.system_prompt import get_configured_system_prompt


def test_compose_returns_base_when_nothing_set():
    # When the global glossary is excluded and no mode/tone/user terms
    # are supplied, the output is exactly the base prompt.
    out = compose_system_prompt(include_global_glossary=False)
    assert out == get_configured_system_prompt()


def test_compose_default_includes_global_glossary():
    # Global glossary is shipped by default — the model needs to know
    # what "GoblinOS" means even if the request didn't supply terms.
    out = compose_system_prompt()
    base = get_configured_system_prompt()
    assert out != base
    assert "GoblinOS:" in out
    # Base prompt still present verbatim.
    assert "GoblinOS Assistant" in out


def test_compose_order_base_then_glossary_then_mode_then_tone():
    """Pins the canonical order: base → glossary → mode → tone."""
    out = compose_system_prompt(
        tone=tone_addendums.ToneMode.FORMAL,
        mode="DEBUG",
        request_glossary={"ACME": "Test project codename"},
        user_glossary=None,
        include_global_glossary=False,
    )

    base_idx = out.find("GoblinOS Assistant")
    glossary_idx = out.find("[GLOSSARY]")
    mode_idx = out.find("[DEBUG MODE]")
    tone_idx = out.find("[TONE: FORMAL]")

    assert base_idx >= 0
    assert glossary_idx > base_idx, "glossary must come after base"
    assert mode_idx > glossary_idx, "mode must come after glossary"
    assert tone_idx > mode_idx, "tone must come after mode"


def test_compose_includes_request_glossary_term():
    out = compose_system_prompt(
        request_glossary={"SENTINEL": "internal codename for the assistant"},
        user_glossary=None,
        include_global_glossary=False,
    )
    assert "SENTINEL: internal codename for the assistant" in out


def test_compose_includes_user_glossary_term():
    out = compose_system_prompt(
        request_glossary=None,
        user_glossary={"BUDGET": "weekly compute budget"},
        include_global_glossary=False,
    )
    assert "BUDGET: weekly compute budget" in out


def test_compose_request_glossary_overrides_user():
    out = compose_system_prompt(
        request_glossary={"Z": "request"},
        user_glossary={"Z": "user"},
        include_global_glossary=False,
    )
    assert "Z: request" in out
    assert "Z: user" not in out


def test_compose_tone_is_optional():
    out_default = compose_system_prompt(tone=None)
    out_explicit = compose_system_prompt(tone=tone_addendums.ToneMode.DEFAULT)
    assert out_default == out_explicit
    assert "[TONE:" not in out_default


def test_compose_mode_is_optional():
    out = compose_system_prompt(mode=None)
    assert "[GENERAL ASSISTANT MODE]" not in out
    assert "[DEEP RESEARCH MODE" not in out
    assert "[DEBUG MODE]" not in out


def test_compose_unknown_mode_raises_by_default():
    with pytest.raises(KeyError):
        compose_system_prompt(mode="DEFINITELY_NOT_A_REAL_MODE", unknown_mode="raise")


def test_compose_unknown_mode_skips_when_configured():
    # The streaming path uses unknown_mode="skip" so a typo on the
    # frontend never breaks the stream.
    out = compose_system_prompt(mode="DEFINITELY_NOT_A_REAL_MODE", unknown_mode="skip")
    # Base prompt still there, no mode addendum injected.
    assert "GoblinOS Assistant" in out
    assert "DEFINITELY_NOT_A_REAL_MODE" not in out


def test_compose_learning_boost_appends_education_addendum():
    out = compose_system_prompt(
        mode="DEBUG",
        learning_boost=True,
        include_global_glossary=False,
    )
    # Mode block + education block.
    assert "[DEBUG MODE]" in out
    assert "comprehension" in out.lower()  # EDUCATION addendum keyword


def test_compose_learning_boost_without_mode_still_works():
    out = compose_system_prompt(
        mode=None,
        learning_boost=True,
        include_global_glossary=False,
    )
    assert "comprehension" in out.lower()


def test_compose_no_learning_boost_omits_education():
    out = compose_system_prompt(
        mode="DEBUG",
        learning_boost=False,
        include_global_glossary=False,
    )
    assert "[DEBUG MODE]" in out
    # No education-specific content when boost is off and no other addendum
    # pulls it in. "concrete numerical example" is education-only.
    assert "concrete numerical example" not in out


def test_compose_global_glossary_can_be_excluded():
    out = compose_system_prompt(include_global_glossary=False)
    # No global terms.
    assert "GoblinOS:" not in out
    # But the base prompt is still there.
    assert "GoblinOS Assistant" in out


def test_compose_returns_non_empty_string_always():
    # Defensive: even with everything None/False, the base prompt guarantees
    # non-empty output, so call sites can always concat the result.
    assert compose_system_prompt() != ""
    assert compose_system_prompt(tone=None, mode=None, learning_boost=False) != ""


def test_compose_blocks_are_double_newline_separated():
    out = compose_system_prompt(
        tone=tone_addendums.ToneMode.CASUAL,
        mode="ARCHITECT",
        request_glossary={"X": "y"},
        include_global_glossary=False,
    )
    # Visible block boundaries with blank lines.
    assert "\n\n[GLOSSARY]" in out
    assert "\n\n[ARCHITECT MODE]" in out
    assert "\n\n[TONE: CASUAL]" in out


def test_compose_tone_unknown_string_does_not_crash():
    # Same defensive behaviour as get_tone_addendum: unknown tones
    # resolve to empty rather than raising.
    out = compose_system_prompt(tone="DEFINITELY_NOT_A_REAL_TONE")
    assert "[TONE:" not in out
