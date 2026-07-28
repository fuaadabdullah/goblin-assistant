"""Privacy and redaction utilities for sensitive content."""

import re


def _redact_sensitive_keywords(text: str) -> str:
    redacted = text
    patterns = [
        r"(?i)\b(password|passcode|pin|secret|token|api[_-]?key|private[_-]?key|cvv|security[_-]?code)\b\s*(?:is|=|:)?\s*[^\s,;]+(?:\s+[^\s,;]+)?",
        r"(?i)\b(password|passcode|pin|secret|token|api[_-]?key|private[_-]?key|cvv|security[_-]?code)\b",
    ]
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    redacted = re.sub(r"(?i)\[REDACTED\]\s+[^\s,;]+", "[REDACTED]", redacted)
    return redacted
