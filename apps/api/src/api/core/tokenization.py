"""
Shared tokenization utilities for API services and config modules.

The implementation prefers `tiktoken` when available and falls back to a
simple character-based estimate when it is not.
"""

from __future__ import annotations

from functools import lru_cache

import structlog

logger = structlog.get_logger()


@lru_cache(maxsize=1)
def _get_encoding():
    """Lazily load the tiktoken encoding (cached after first call)."""
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        logger.warning("tiktoken_unavailable", error=str(e), fallback="len//4")
        return None


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken, falling back to len//4."""
    if not text:
        return 0
    enc = _get_encoding()
    if enc is not None:
        return len(enc.encode(text))
    return len(text) // 4


def trim_to_tokens(text: str, max_tokens: int) -> str:
    """Trim text to fit within a token limit, preserving sentence boundaries."""
    if not text or max_tokens <= 0:
        return ""

    enc = _get_encoding()

    if enc is not None:
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated = enc.decode(tokens[:max_tokens])
        last_period = truncated.rfind(". ")
        if last_period > len(truncated) // 2:
            truncated = truncated[: last_period + 1]
        return truncated + "\n\n[... content truncated due to token limits ...]"

    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text

    sentences = text.split(". ")
    trimmed = ""
    for sentence in sentences:
        if len(trimmed + sentence) > max_chars - 50:
            break
        trimmed += sentence + ". "

    if not trimmed:
        trimmed = text[: max_chars - 50]

    return trimmed + "\n\n[... content truncated due to token limits ...]"


__all__ = ["count_tokens", "trim_to_tokens"]
