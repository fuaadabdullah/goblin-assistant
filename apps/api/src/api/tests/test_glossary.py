"""Tests for the glossary registry."""

from __future__ import annotations

from api.config import glossary


def test_global_glossary_has_stable_terms():
    # Sanity: the global glossary is a non-empty dict of string→string.
    assert glossary.GLOBAL_GLOSSARY
    for term, definition in glossary.GLOBAL_GLOSSARY.items():
        assert isinstance(term, str) and term.strip()
        assert isinstance(definition, str) and definition.strip()


def test_resolve_glossary_request_overrides_user_overrides_global():
    merged = glossary.resolve_glossary(
        request_glossary={"X": "request-X"},
        user_glossary={"X": "user-X", "Y": "user-Y"},
        include_global=True,
    )
    # Request wins over user wins over global.
    assert merged["X"] == "request-X"
    assert merged["Y"] == "user-Y"


def test_resolve_glossary_user_fills_missing_global_terms():
    merged = glossary.resolve_glossary(
        request_glossary=None,
        user_glossary={"X": "user-X"},
        include_global=True,
    )
    # Global terms are still present.
    assert "GoblinOS" in merged
    # User term is included.
    assert merged["X"] == "user-X"


def test_resolve_glossary_can_drop_global():
    merged = glossary.resolve_glossary(
        request_glossary={"X": "x"},
        user_glossary=None,
        include_global=False,
    )
    # No global terms.
    assert "GoblinOS" not in merged
    assert merged == {"X": "x"}


def test_resolve_glossary_drops_falsy_entries():
    merged = glossary.resolve_glossary(
        request_glossary={"": "empty-term", "valid": "valid-def", "x": ""},
        user_glossary=None,
        include_global=False,
    )
    assert "valid" in merged
    assert "" not in merged
    assert "x" not in merged


def test_resolve_glossary_accepts_iterable_of_tuples():
    merged = glossary.resolve_glossary(
        request_glossary=[("alpha", "first"), ("beta", "second")],
        user_glossary=None,
        include_global=False,
    )
    assert merged == {"alpha": "first", "beta": "second"}


def test_format_glossary_addendum_empty_when_no_terms():
    # When global is excluded and no user/request terms, no addendum.
    out = glossary.format_glossary_addendum(
        request_glossary=None, user_glossary=None, include_global=False
    )
    assert out == ""


def test_format_glossary_addendum_includes_global_by_default():
    out = glossary.format_glossary_addendum()
    assert "[GLOSSARY]" in out
    assert "GoblinOS" in out
    # Format is one bullet per term.
    assert "- GoblinOS:" in out


def test_format_glossary_addendum_request_terms_appear():
    out = glossary.format_glossary_addendum(
        request_glossary={"ACME": "Project codename"},
        user_glossary=None,
        include_global=False,
    )
    assert "ACME: Project codename" in out


def test_format_glossary_addendum_caps_terms():
    big = {f"term{i}": f"def{i}" for i in range(50)}
    out = glossary.format_glossary_addendum(
        request_glossary=big,
        user_glossary=None,
        include_global=False,
        max_terms=10,
    )
    # 10 bullets max, regardless of how many terms are passed.
    bullet_count = out.count("\n- ")
    assert bullet_count == 10


def test_list_global_terms_returns_sorted():
    terms = glossary.list_global_terms()
    assert terms == sorted(terms)
    assert "GoblinOS" in terms
