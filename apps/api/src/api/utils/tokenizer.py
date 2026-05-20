"""
Token counting utility using tiktoken for accurate token budgeting.

Uses cl100k_base encoding by default (GPT-4 / GPT-3.5-turbo compatible).
Falls back to len(text) // 4 if tiktoken is unavailable.
"""

import structlog

logger = structlog.get_logger()

_encoding = None
_fallback_mode = False


def _get_encoding():
    """Lazily load the tiktoken encoding (cached after first call)."""
    global _encoding, _fallback_mode
    if _encoding is not None:
        return _encoding
    if _fallback_mode:
        return None
    try:
        import tiktoken
        _encoding = tiktoken.get_encoding("cl100k_base")
        return _encoding
    except Exception as e:
        logger.warning("tiktoken_unavailable", error=str(e), fallback="len//4")
        _fallback_mode = True
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
    """Trim text to fit within a token limit, preserving sentence boundaries.

    Uses tiktoken for precise trimming when available, otherwise
    falls back to character-based estimation.
    """
    if not text or max_tokens <= 0:
        return ""

    enc = _get_encoding()

    if enc is not None:
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        # Decode the truncated token list back to text
        truncated = enc.decode(tokens[:max_tokens])
        # Try to break at the last sentence boundary
        last_period = truncated.rfind(". ")
        if last_period > len(truncated) // 2:
            truncated = truncated[: last_period + 1]
        return truncated + "\n\n[... content truncated due to token limits ...]"

    # Fallback: character-based estimation
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
