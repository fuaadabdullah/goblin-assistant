from __future__ import annotations

from api.routing.keyword_matcher import keyword_matches_text


def test_keyword_matcher_does_not_match_embedded_substrings():
    text = "What is the latest on AI policy?"

    assert not keyword_matches_text(text, "test")
    assert not keyword_matches_text(text, "api")


def test_keyword_matcher_still_handles_typo_tolerance():
    assert keyword_matches_text("Summrize this arcticle about climate change", "summarize")
    assert keyword_matches_text(
        "Can you reseach the latets current developments in AI policy?",
        "research",
    )


def test_keyword_matcher_still_matches_short_exact_tokens():
    assert keyword_matches_text("Open the API endpoint", "api")
