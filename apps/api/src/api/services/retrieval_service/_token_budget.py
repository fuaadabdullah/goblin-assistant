"""
Pure token budgeting utilities for the RetrievalService.

All functions are stateless/pure: they operate on provided data structures
and return results without side effects.
"""

from typing import Any, Dict, List, Optional


def estimate_tokens(content: str) -> int:
    """Rough token estimate used for context budgeting."""
    if not content:
        return 0
    return max(1, (len(content) + 3) // 4)


def trim_item_to_token_budget(
    item: Dict[str, Any],
    remaining_tokens: int,
) -> Optional[Dict[str, Any]]:
    """Trim a single item's content to fit within *remaining_tokens*.

    Returns ``None`` if the item cannot be included at all.
    """
    if remaining_tokens <= 0:
        return None

    content = item.get("content", "")
    if not content:
        return None

    item_tokens = estimate_tokens(content)
    if item_tokens <= remaining_tokens:
        return dict(item)

    allowed_chars = remaining_tokens * 4
    if allowed_chars <= 0:
        return None

    trimmed_content = content[:allowed_chars]
    if not trimmed_content:
        return None

    trimmed_item = dict(item)
    trimmed_item["content"] = trimmed_content
    metadata = dict(trimmed_item.get("metadata") or {})
    metadata["truncated_for_token_budget"] = True
    trimmed_item["metadata"] = metadata
    return trimmed_item


def apply_context_token_budget(
    context_bundle: Dict[str, Any],
    max_tokens: int,
) -> int:
    """Apply a token budget to *context_bundle*, trimming in priority order.

    Priority order (highest → lowest):
        1. memory_facts
        2. summaries
        3. documents  (PDFs, code, research — durable, no expiry)
        4. messages
        5. ephemeral_messages
        6. tasks

    Returns the total number of tokens kept.
    """
    if max_tokens <= 0:
        for bucket in (
            "memory_facts",
            "summaries",
            "documents",
            "messages",
            "ephemeral_messages",
            "tasks",
        ):
            context_bundle[bucket] = []
        return 0

    priority_buckets = [
        "memory_facts",
        "summaries",
        "documents",
        "messages",
        "ephemeral_messages",
        "tasks",
    ]
    kept_items: Dict[str, List[Dict[str, Any]]] = {bucket: [] for bucket in priority_buckets}
    total_tokens = 0

    for bucket in priority_buckets:
        for item in context_bundle.get(bucket, []):
            remaining_tokens = max_tokens - total_tokens
            if remaining_tokens <= 0:
                break

            trimmed_item = trim_item_to_token_budget(item, remaining_tokens)
            if not trimmed_item:
                continue

            item_tokens = estimate_tokens(trimmed_item.get("content", ""))
            if item_tokens <= 0:
                continue

            kept_items[bucket].append(trimmed_item)
            total_tokens += item_tokens

            if total_tokens >= max_tokens:
                break

    for bucket in priority_buckets:
        context_bundle[bucket] = kept_items[bucket]

    return total_tokens
