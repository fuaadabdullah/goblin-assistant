"""Shared fuzzy keyword matching helpers for routing classifiers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable

_WORD_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "around",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "these",
    "this",
    "those",
    "to",
    "through",
    "with",
    "your",
}


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _token_threshold(token: str) -> float:
    if len(token) <= 2:
        return 1.0
    if len(token) == 3:
        # Short tokens are too ambiguous for fuzzy matching; require an exact hit.
        return 1.0
    if len(token) <= 5:
        return 0.75
    return 0.82


def _token_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    if left.isdigit() or right.isdigit():
        return 1.0 if left == right else 0.0
    shorter_len = min(len(left), len(right))
    length_gap = abs(len(left) - len(right))
    if shorter_len <= 4 and length_gap > 1:
        return 0.0
    if left in right or right in left:
        shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
        if len(shorter) >= 4 and len(longer) - len(shorter) <= 2:
            return 0.9
    return SequenceMatcher(None, left, right).ratio()


def keyword_matches_text(text: str, keyword: str) -> bool:
    """Return True when keyword appears in text, allowing small spelling mistakes."""
    prompt_tokens = _tokenize(text)
    if not prompt_tokens:
        return False

    keyword_tokens = [token for token in _tokenize(keyword) if token not in _STOPWORDS]
    if not keyword_tokens:
        return False

    remaining_prompt_tokens = list(prompt_tokens)
    for keyword_token in keyword_tokens:
        best_index = -1
        best_ratio = 0.0
        threshold = _token_threshold(keyword_token)
        for index, prompt_token in enumerate(remaining_prompt_tokens):
            ratio = _token_similarity(prompt_token, keyword_token)
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = index
        if best_index < 0 or best_ratio < threshold:
            return False
        remaining_prompt_tokens.pop(best_index)

    return True


def contains_any_keywords(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword_matches_text(text, keyword) for keyword in keywords)
