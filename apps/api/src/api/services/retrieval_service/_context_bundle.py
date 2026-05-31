"""
Context bundle assembly for the RetrievalService.

Builds the structured ``get_context_bundle`` result from a flat list of
retrieved items, grouping by source type and applying a token budget.

All functions here are pure/synchronous — no side effects or DB access.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ._token_budget import apply_context_token_budget


def build_context_bundle(
    query: str,
    user_id: str,
    conversation_id: Optional[str],
    all_context: List[Dict[str, Any]],
    max_tokens: int,
    degraded_status: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a structured context bundle from retrieval results.

    Groups *all_context* by ``source_type``, applies a token budget,
    and returns a fully populated bundle dict.
    """
    context_bundle: Dict[str, Any] = {
        "query": query,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "retrieved_at": datetime.utcnow().isoformat(),
        "summaries": [],
        "messages": [],
        "ephemeral_messages": [],
        "tasks": [],
        "memory_facts": [],
        "total_tokens": 0,
        "metadata": {},
    }

    # Group by source type
    for item in all_context:
        source_type = item.get("source_type", "")
        if source_type == "summary":
            context_bundle["summaries"].append(item)
        elif source_type == "message":
            context_bundle["messages"].append(item)
        elif source_type == "ephemeral":
            context_bundle["ephemeral_messages"].append(item)
        elif source_type == "task":
            context_bundle["tasks"].append(item)
        elif source_type == "memory":
            context_bundle["memory_facts"].append(item)

    # Enforce context budget by source priority
    total_tokens = apply_context_token_budget(context_bundle, max_tokens=max_tokens)

    context_bundle["total_tokens"] = total_tokens
    context_bundle["token_estimate"] = total_tokens
    context_bundle["metadata"]["context_count"] = len(all_context)
    context_bundle["metadata"]["max_tokens_applied"] = True
    context_bundle["metadata"]["max_tokens"] = max_tokens
    context_bundle["metadata"].update(degraded_status)

    return context_bundle
