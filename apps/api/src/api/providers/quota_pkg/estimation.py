"""Character-based token estimation, decoupled from retrieval-service imports."""

from __future__ import annotations


def estimate_text_tokens(content: str) -> int:
    """Keep quota estimation independent from retrieval-service import wiring."""
    if not content:
        return 0
    return max(1, (len(content) + 3) // 4)
