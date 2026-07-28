"""
Write-capable memory tool for Goblin Assistant.

Allows the model to deliberately store facts, preferences, and goals
into long-term memory during conversations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from api.services.memory_core import memory_core_service

from ..registry import ToolDefinition, ToolParameter, register_tool

_CATEGORY_ALIASES = {
    "preference": ("preference", "preference"),
    "fact": ("fact", "fact"),
    "goal": ("goal", "goal"),
    "project": ("project", "project_state"),
    "project_state": ("project", "project_state"),
    "correction": ("correction", "correction"),
    "decision": ("fact", "decision"),
    "relationship": ("fact", "relationship"),
    "task_signal": ("goal", "task_signal"),
}


def _normalize_memory_category(category: Optional[str]) -> tuple[str, str]:
    raw = str(category).strip().lower() if category else "preference"
    return _CATEGORY_ALIASES.get(raw, ("preference", "preference"))


async def _handle_memory_write(
    fact: str,
    category: str = "preference",
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Store a fact into long-term memory."""
    if not fact or not str(fact).strip():
        return {"error": "fact is required"}
    if not user_id or not str(user_id).strip():
        return {"error": "user_id is required"}

    valid_categories = set(_CATEGORY_ALIASES.keys())
    safe_category = str(category).strip().lower() if category else "preference"
    if safe_category not in valid_categories:
        safe_category = "preference"
    display_category, storage_category = _normalize_memory_category(safe_category)

    try:
        await memory_core_service.ingest_memory_fact(
            user_id=str(user_id),
            fact_text=str(fact),
            category=storage_category,
            source_kind="tool",
            source_id=conversation_id or "memory_write_tool",
            confidence=0.85,
            metadata={
                "from_tool": "memory_write",
                "conversation_id": conversation_id,
                "requested_category": display_category,
                "storage_category": storage_category,
            },
            explicit_kind=storage_category,
        )

        return {
            "status": "stored",
            "fact": str(fact),
            "category": display_category,
            "storage_category": storage_category,
            "user_id": user_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "fact": str(fact),
        }


register_tool(
    ToolDefinition(
        name="memory_write",
        description=(
            "Store a fact, preference, project, goal, relationship, or correction into "
            "long-term user memory. Use this when you want to deliberately capture and persist "
            "information about the user for future conversations instead of storing raw chat. "
            "Examples: 'I trade small caps using VWAP', 'I prefer concise responses', "
            "'My main goal is building a $75k account', 'Do not use tool X', "
            "'GoblinOS is the active project'."
        ),
        parameters=[
            ToolParameter(
                name="fact",
                type="string",
                description=(
                    "The fact or statement to store. Should be a complete, self-contained sentence. "
                    "Examples: 'User trades with CMEG broker', 'Prefers Python over JavaScript', "
                    "'Project is GoblinOS', 'Goal is to launch beta', 'Correction: avoid X'."
                ),
            ),
            ToolParameter(
                name="category",
                type="string",
                description=(
                    "Category of the memory. One of: 'preference', 'fact', 'goal', 'project', "
                    "'project_state', 'correction', 'decision', 'relationship', 'task_signal'. "
                    "Defaults to 'preference'."
                ),
                required=False,
                default="preference",
            ),
            ToolParameter(
                name="user_id",
                type="string",
                description="Authenticated user id. Provided by runtime context.",
            ),
            ToolParameter(
                name="conversation_id",
                type="string",
                description="Optional conversation scope for traceability.",
                required=False,
            ),
        ],
        handler=_handle_memory_write,
        category="memory",
    )
)
