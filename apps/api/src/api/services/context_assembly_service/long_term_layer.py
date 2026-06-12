"""
Long‑Term Memory layer assembler.

Always included if available, but capped to a small token budget.
Last to be dropped if the window is exhausted.
"""

from typing import Any, Dict, List, Optional

import structlog

from ...storage.database import get_readonly_db_context
from ...storage.vector_models import MemoryFactModel
from ...utils.tokenizer import count_tokens, trim_to_tokens
from .models import ContextBudget, ContextLayer

logger = structlog.get_logger()


async def get_long_term_memory_facts(user_id: str) -> List[Dict[str, Any]]:
    """Retrieve long‑term memory facts for *user_id*."""
    try:
        from sqlalchemy import select

        async with get_readonly_db_context() as session:
            stmt = (
                select(MemoryFactModel)
                .filter(MemoryFactModel.user_id == user_id)
                .order_by(MemoryFactModel.created_at.desc())
                .limit(10)
            )

            result = await session.execute(stmt)
            facts = []
            for fact in result.scalars():
                facts.append(
                    {
                        "content": fact.fact_text,
                        "category": fact.category,
                        "memory_type": getattr(fact, "memory_type", None) or fact.category,
                        "created_at": fact.created_at.isoformat(),
                    }
                )
            return facts
    except Exception as e:
        logger.error("Failed to retrieve long-term memory facts", error=str(e))
        return []


def format_long_term_memory(facts: List[Dict[str, Any]]) -> str:
    """Level 2 compression: format long‑term memory facts as bullet points."""
    if not facts:
        return ""

    lines = ["## User Preferences & Stable Facts"]
    for fact in facts:
        memory_type = fact.get("memory_type") or fact.get("category") or "fact"
        lines.append(f"- [{memory_type}] {fact['content']} (Category: {fact['category']})")
    return "\n".join(lines)


def _cluster_sentence(entity_type: str, entity_value: str, contents: List[str]) -> str:
    first = contents[0][:120]
    joined = ", ".join(c[:80] for c in contents)[:200]
    if entity_type == "project":
        return f"Working on {entity_value}: {joined}."
    if entity_type == "preference":
        return f"Prefers {entity_value}: {first}."
    if entity_type == "decision":
        return f"Decided: {first}."
    if entity_value and entity_value != "general":
        return f"{entity_value}: {first}."
    return first + "."


def build_session_memory_pack(facts: List[Dict[str, Any]]) -> str:
    """Level 3 compression: group memories by entity and produce one sentence per cluster."""
    if not facts:
        return ""

    clusters: dict = {}
    for fact in facts:
        entity_refs = fact.get("entity_refs") or []
        if entity_refs and isinstance(entity_refs[0], dict):
            key = (str(entity_refs[0].get("type", "")), str(entity_refs[0].get("value", "")))
        else:
            key = (str(fact.get("memory_type") or fact.get("category") or "fact"), "general")
        clusters.setdefault(key, []).append(str(fact.get("content", "")))

    sentences = [
        _cluster_sentence(entity_type, entity_value, contents)
        for (entity_type, entity_value), contents in clusters.items()
    ]
    return "User context: " + " ".join(sentences)


async def assemble_long_term_memory(
    user_id: str,
    remaining_tokens: int,
    budget: ContextBudget,
    compression_level: int = 2,
) -> Optional[ContextLayer]:
    """Assemble Long‑Term Memory layer (Always, but tiny).

    compression_level=2 (default): bullet-point format.
    compression_level=3: compact session pack sentence.
    Falls back to level 3 automatically when token budget is tight.
    """
    if remaining_tokens < budget.long_term_tokens:
        return None

    try:
        memory_facts = await get_long_term_memory_facts(user_id)
        if not memory_facts:
            return None

        use_pack = compression_level >= 3 or remaining_tokens < budget.long_term_tokens * 2
        if use_pack:
            memory_content = build_session_memory_pack(memory_facts)
            used_compression = 3
        else:
            memory_content = format_long_term_memory(memory_facts)
            used_compression = 2

        tokens = count_tokens(memory_content)

        if tokens > budget.long_term_tokens:
            memory_content = trim_to_tokens(memory_content, budget.long_term_tokens)
            tokens = budget.long_term_tokens

        return ContextLayer(
            name="long_term_memory",
            content=memory_content,
            tokens=tokens,
            source_count=len(memory_facts),
            metadata={
                "type": "long_term",
                "source_count": len(memory_facts),
                "description": "User preferences and stable facts",
                "compression_level": used_compression,
            },
        )
    except Exception as e:
        logger.error("Failed to assemble long-term memory", error=str(e))
        return None
