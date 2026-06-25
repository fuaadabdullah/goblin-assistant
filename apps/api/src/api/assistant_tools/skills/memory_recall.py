"""
Read-only memory recall tool for Goblin Assistant.

Exposes relevant long-term memory facts so the model can intentionally
request memory context during tool-calling loops.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from api.services.memory_core import memory_core_service

from ..registry import ToolDefinition, ToolParameter, register_tool


async def _handle_memory_recall(
    query: str,
    user_id: str,
    conversation_id: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    if not query or not str(query).strip():
        return {"error": "query is required"}
    if not user_id or not str(user_id).strip():
        return {"error": "user_id is required"}

    safe_limit = max(1, min(int(limit), 10))
    facts = await memory_core_service.retrieve_memory_context(
        user_id=user_id,
        query=str(query),
        limit=safe_limit,
    )

    normalized = []
    for fact in facts:
        normalized.append(
            {
                "id": fact.get("id"),
                "content": fact.get("content", ""),
                "category": fact.get("category"),
                "memory_type": fact.get("memory_type"),
                "score": fact.get("score", 0.0),
                "rerank_score": fact.get("rerank_score", 0.0),
                "created_at": (
                    fact.get("created_at").isoformat()
                    if hasattr(fact.get("created_at"), "isoformat")
                    else fact.get("created_at")
                ),
                "metadata": fact.get("metadata", {}),
            }
        )

    return {
        "query": str(query),
        "user_id": user_id,
        "conversation_id": conversation_id,
        "count": len(normalized),
        "memory_facts": normalized,
    }


register_tool(
    ToolDefinition(
        name="memory_recall",
        description=(
            "Use when you need user-specific memory facts relevant to the "
            "current request. Read-only: retrieves prior long-term memory "
            "facts and does not write or modify memory."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Natural-language query used to retrieve relevant memory facts.",
            ),
            ToolParameter(
                name="user_id",
                type="string",
                description=(
                    "Authenticated user id scope for memory retrieval. Provided by runtime context."
                ),
            ),
            ToolParameter(
                name="conversation_id",
                type="string",
                description="Optional conversation scope hint.",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum facts to return. Defaults to 5 (clamped 1-10).",
                required=False,
                default=5,
            ),
        ],
        handler=_handle_memory_recall,
        category="memory",
    )
)
