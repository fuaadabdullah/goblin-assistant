"""
Ephemeral Memory layer assembler.

Formats recent conversation messages and applies a summary‑fallback
strategy when the remaining budget is too small.
"""

from typing import Dict, List, Optional

import structlog

from ...utils.tokenizer import count_tokens, trim_to_tokens
from .models import ContextBudget, ContextLayer

logger = structlog.get_logger()


def format_ephemeral_memory(history: List[Dict[str, str]]) -> str:
    """Format recent conversation history."""
    if not history:
        return ""

    lines = ["## Recent Messages"]
    for msg in history[-5:]:
        lines.append(f"{msg['role']}: {msg['content']}")
    return "\n".join(lines)


def build_ephemeral_summary(history: List[Dict[str, str]]) -> str:
    """Build concise summary fallback for trimmed ephemeral context."""
    if not history:
        return ""

    older_messages = history[:-5]
    if not older_messages:
        return ""

    lines = [
        "## Ephemeral Summary (truncated)",
        f"- {len(older_messages)} earlier messages were condensed due to token limits.",
    ]

    for msg in older_messages[-3:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "").strip().replace("\n", " ")
        if len(content) > 120:
            content = f"{content[:117].rstrip()}..."
        lines.append(f"- {role}: {content}")

    return "\n".join(lines)


async def assemble_ephemeral_memory(
    conversation_history: List[Dict[str, str]],
    remaining_tokens: int,
    budget: ContextBudget,
) -> Optional[ContextLayer]:
    """Assemble Ephemeral Memory layer (Recent Messages)."""
    effective_limit = min(remaining_tokens, budget.ephemeral_tokens)
    if effective_limit < 50:
        return None

    try:
        recent_content = format_ephemeral_memory(conversation_history)
        tokens = count_tokens(recent_content)
        original_tokens = tokens
        truncated = False
        summary_fallback_applied = False

        if tokens > effective_limit:
            truncated = True
            summary_fallback = build_ephemeral_summary(conversation_history)
            if summary_fallback:
                summary_tokens = count_tokens(summary_fallback)
                if summary_tokens < effective_limit:
                    remaining_after_summary = max(0, effective_limit - summary_tokens)
                    trimmed_recent = trim_to_tokens(recent_content, remaining_after_summary)
                    recent_content = f"{summary_fallback}\n\n{trimmed_recent}"
                    summary_fallback_applied = True
                else:
                    recent_content = trim_to_tokens(summary_fallback, effective_limit)
                    summary_fallback_applied = True
            else:
                recent_content = trim_to_tokens(recent_content, effective_limit)
            tokens = effective_limit

        return ContextLayer(
            name="ephemeral_memory",
            content=recent_content,
            tokens=tokens,
            source_count=len(conversation_history),
            metadata={
                "type": "ephemeral",
                "source_count": len(conversation_history),
                "description": "Recent conversation messages",
                "truncated": truncated,
                "summary_fallback_applied": summary_fallback_applied,
                "original_tokens": original_tokens,
            },
        )
    except Exception as e:
        logger.error("Failed to assemble ephemeral memory", error=str(e))
        return None
