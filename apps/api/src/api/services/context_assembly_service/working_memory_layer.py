"""
Working Memory layer assembler.

Retrieves conversation summaries and formats them for the context window.
"""

from typing import Any, Dict, List, Optional

import structlog

from ...storage.database import get_db
from ...storage.vector_models import ConversationSummaryModel
from ...utils.tokenizer import count_tokens, trim_to_tokens
from .models import ContextBudget, ContextLayer

logger = structlog.get_logger()


async def get_working_memory_summaries(
    user_id: str,
    conversation_id: str,
) -> List[Dict[str, Any]]:
    """Retrieve working memory summaries for a conversation."""
    try:
        from sqlalchemy import select

        async with get_db() as session:
            stmt = (
                select(ConversationSummaryModel)
                .filter(ConversationSummaryModel.user_id == user_id)
                .filter(ConversationSummaryModel.conversation_id == conversation_id)
                .order_by(ConversationSummaryModel.created_at.desc())
                .limit(5)
            )

            result = await session.execute(stmt)
            summaries = []
            for summary in result.scalars():
                summaries.append(
                    {
                        "content": summary.summary_text,
                        "created_at": summary.created_at.isoformat(),
                    }
                )
            return summaries
    except Exception as e:
        logger.error("Failed to retrieve working memory summaries", error=str(e))
        return []


def format_working_memory(summaries: List[Dict[str, Any]]) -> str:
    """Format working memory summaries."""
    if not summaries:
        return ""

    lines = ["## Current Conversation Context"]
    for summary in summaries:
        lines.append(f"- {summary['content']}")
    return "\n".join(lines)


async def assemble_working_memory(
    user_id: str,
    conversation_id: str,
    remaining_tokens: int,
    budget: ContextBudget,
) -> Optional[ContextLayer]:
    """Assemble Working Memory layer (Summaries)."""
    if remaining_tokens < budget.working_memory_tokens:
        return None

    try:
        summaries = await get_working_memory_summaries(user_id, conversation_id)
        if not summaries:
            return None

        summary_content = format_working_memory(summaries)
        tokens = count_tokens(summary_content)

        if tokens > budget.working_memory_tokens:
            summary_content = trim_to_tokens(
                summary_content, budget.working_memory_tokens
            )
            tokens = budget.working_memory_tokens

        return ContextLayer(
            name="working_memory",
            content=summary_content,
            tokens=tokens,
            source_count=len(summaries),
            metadata={
                "type": "working_memory",
                "source_count": len(summaries),
                "description": "Conversation and task summaries",
            },
        )
    except Exception as e:
        logger.error("Failed to assemble working memory", error=str(e))
        return None
