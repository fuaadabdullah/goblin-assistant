"""
Read-only memory recall tool for Goblin Assistant.

Exposes relevant long-term memory facts so the model can intentionally
request memory context during tool-calling loops.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from api.services.memory_core import memory_core_service
from api.services.retrieval_service._limits import clamp_memory_search_limit

from ..registry import ToolDefinition, ToolParameter, register_tool


async def _handle_memory_recall(
    query: str,
    user_id: str,
    conversation_id: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    if not query or not str(query).strip():
        return {"error": "query is required"}
    if not user_id or not str(user_id).strip():
        return {"error": "user_id is required"}

    safe_limit = clamp_memory_search_limit(limit)
    facts = await memory_core_service.retrieve_memory_context(
        user_id=user_id,
        query=str(query),
        limit=safe_limit,
    )

    normalized = []
    for fact in facts:
        embedding = fact.get("embedding") or fact.get("fact_embedding") or []
        if not isinstance(embedding, list):
            if isinstance(embedding, tuple):
                embedding = list(embedding)
            else:
                embedding = []
        normalized.append(
            {
                "id": fact.get("id"),
                "text": fact.get("text") or fact.get("content", ""),
                "content": fact.get("content", ""),
                "category": fact.get("category"),
                "memory_type": fact.get("memory_type"),
                "score": fact.get("score", 0.0),
                "rerank_score": fact.get("rerank_score", 0.0),
                "createdAt": (
                    fact.get("createdAt")
                    or (
                        fact.get("created_at").isoformat()
                        if hasattr(fact.get("created_at"), "isoformat")
                        else fact.get("created_at")
                    )
                ),
                "created_at": (
                    fact.get("created_at").isoformat()
                    if hasattr(fact.get("created_at"), "isoformat")
                    else fact.get("created_at")
                ),
                "updatedAt": (
                    fact.get("updatedAt")
                    or (
                        fact.get("updated_at").isoformat()
                        if hasattr(fact.get("updated_at"), "isoformat")
                        else fact.get("updated_at")
                    )
                ),
                "updated_at": (
                    fact.get("updated_at").isoformat()
                    if hasattr(fact.get("updated_at"), "isoformat")
                    else fact.get("updated_at")
                ),
                "lastAccessed": (
                    fact.get("lastAccessed")
                    or (
                        fact.get("last_accessed_at").isoformat()
                        if hasattr(fact.get("last_accessed_at"), "isoformat")
                        else fact.get("last_accessed_at")
                    )
                ),
                "last_accessed_at": (
                    fact.get("last_accessed_at").isoformat()
                    if hasattr(fact.get("last_accessed_at"), "isoformat")
                    else fact.get("last_accessed_at")
                ),
                "expiresAt": (
                    fact.get("expiresAt")
                    or (
                        fact.get("expires_at").isoformat()
                        if hasattr(fact.get("expires_at"), "isoformat")
                        else fact.get("expires_at")
                    )
                ),
                "expires_at": (
                    fact.get("expires_at").isoformat()
                    if hasattr(fact.get("expires_at"), "isoformat")
                    else fact.get("expires_at")
                ),
                "embedding": embedding,
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
                description="Maximum facts to return. Defaults to 10 (clamped 1-20).",
                required=False,
                default=10,
            ),
        ],
        handler=_handle_memory_recall,
        category="memory",
    )
)
