"""
Long‑Term Memory layer assembler.

Always included if available, but capped to a small token budget.
Last to be dropped if the window is exhausted.
"""

from typing import Any, Dict, List, Optional

import structlog

from ...storage.database import get_db
from ...storage.vector_models import MemoryFactModel
from ...utils.tokenizer import count_tokens, trim_to_tokens
from .models import ContextBudget, ContextLayer

logger = structlog.get_logger()


async def get_long_term_memory_facts(user_id: str) -> List[Dict[str, Any]]:
    """Retrieve long‑term memory facts for *user_id*."""
    try:
        from sqlalchemy import select

        async with get_db() as session:
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
                        "created_at": fact.created_at.isoformat(),
                    }
                )
            return facts
    except Exception as e:
        logger.error("Failed to retrieve long-term memory facts", error=str(e))
        return []


def format_long_term_memory(facts: List[Dict[str, Any]]) -> str:
    """Format long‑term memory facts as bullet points."""
    if not facts:
        return ""

    lines = ["## User Preferences & Stable Facts"]
    for fact in facts:
        lines.append(f"- {fact['content']} (Category: {fact['category']})")
    return "\n".join(lines)


async def assemble_long_term_memory(
    user_id: str,
    remaining_tokens: int,
    budget: ContextBudget,
) -> Optional[ContextLayer]:
    """Assemble Long‑Term Memory layer (Always, but tiny)."""
    if remaining_tokens < budget.long_term_tokens:
        return None

    try:
        memory_facts = await get_long_term_memory_facts(user_id)
        if not memory_facts:
            return None

        memory_content = format_long_term_memory(memory_facts)
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
            },
        )
    except Exception as e:
        logger.error("Failed to assemble long-term memory", error=str(e))
        return None
