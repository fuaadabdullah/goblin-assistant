"""
Semantic Retrieval layer assembler.

Runs vector search via the retrieval service, traces it, and trims to
the remaining token budget (hard stop: vector results get cut first).
"""

from typing import Any, Dict, List, Optional

import structlog

from ...observability.retrieval_tracer import retrieval_tracer
from ...utils.tokenizer import count_tokens, trim_to_tokens
from .models import ContextBudget, ContextLayer

logger = structlog.get_logger()


def _get_retrieval_service():
    """Lazy import to avoid circular dependency."""
    from ..retrieval_service import retrieval_service

    return retrieval_service


def format_semantic_retrieval(results: List[Dict[str, Any]]) -> str:
    """Format semantic retrieval results."""
    if not results:
        return ""

    lines = ["## Relevant Context"]
    for i, result in enumerate(results):
        lines.append(f"### Result {i + 1} (Score: {result.get('score', 0):.2f})")
        lines.append(result.get("content", ""))
        lines.append("")
    return "\n".join(lines)


async def assemble_semantic_retrieval(
    query: str,
    user_id: str,
    conversation_id: Optional[str],
    remaining_tokens: int,
    correlation_id: str,
    budget: ContextBudget,
) -> Optional[ContextLayer]:
    """Assemble Semantic Retrieval layer (Vector Results)."""
    if remaining_tokens < 100:
        return None

    retrieval_service = _get_retrieval_service()

    try:
        trace_id = await retrieval_tracer.start_trace(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
        )

        context_results = await retrieval_service.retrieve_context(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            k=10,
            max_age_hours=168,
        )

        if not context_results:
            await retrieval_tracer.end_trace(
                trace_id=trace_id, results_count=0, status="no_results"
            )
            return None

        await retrieval_tracer.record_tier_breakdown(
            trace_id=trace_id,
            tier="semantic_retrieval",
            results=context_results,
            total_results=len(context_results),
        )

        semantic_content = format_semantic_retrieval(context_results)
        tokens = count_tokens(semantic_content)

        hard_stop_applied = False
        if tokens > remaining_tokens:
            semantic_content = trim_to_tokens(semantic_content, remaining_tokens)
            tokens = remaining_tokens
            hard_stop_applied = True

        await retrieval_tracer.end_trace(
            trace_id=trace_id,
            results_count=len(context_results),
            total_tokens=tokens,
            status="success",
            hard_stop_applied=hard_stop_applied,
        )

        return ContextLayer(
            name="semantic_retrieval",
            content=semantic_content,
            tokens=tokens,
            source_count=len(context_results),
            metadata={
                "type": "semantic",
                "source_count": len(context_results),
                "description": "Vector search results",
                "hard_stop_applied": hard_stop_applied,
                "trace_id": trace_id,
            },
        )

    except Exception as e:
        logger.error("Failed to assemble semantic retrieval", error=str(e))
        if "trace_id" in locals():
            await retrieval_tracer.end_trace(
                trace_id=trace_id, results_count=0, status="error", error=str(e)
            )
        return None
