"""Pure functions for handling attachment context limits and injection."""

import os
from typing import Any

from ...services.pdf_extraction_service import (
    DEFAULT_MAX_CONTEXT_CHARS,
    DEFAULT_MAX_CONTEXT_CHUNKS,
)


def attachment_context_limits() -> tuple[int, int]:
    """Read attachment context limits from environment with fallback defaults."""
    max_chunks = int(
        os.getenv("GOBLIN_ATTACHMENT_CONTEXT_MAX_CHUNKS", str(DEFAULT_MAX_CONTEXT_CHUNKS))
    )
    max_chars = int(
        os.getenv("GOBLIN_ATTACHMENT_CONTEXT_MAX_CHARS", str(DEFAULT_MAX_CONTEXT_CHARS))
    )
    return max_chunks, max_chars


def inject_attachment_context(messages: list[dict[str, Any]], attachment_context: str) -> None:
    """Inject extracted attachment context into the first system message.

    Mutates *messages* in place. If no system message exists a new one is
    prepended. This is a controlled side-effect helper used only within the
    message-building pipeline.
    """
    if not attachment_context:
        return
    context_block = f"\n\n{attachment_context}"
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = f"{messages[0].get('content', '')}{context_block}"
        return
    messages.insert(
        0,
        {
            "role": "system",
            "content": attachment_context,
        },
    )
