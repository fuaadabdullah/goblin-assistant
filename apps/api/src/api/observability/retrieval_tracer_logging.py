from __future__ import annotations

import asyncio
from typing import Any


def build_log_data(trace: Any) -> dict:
    return {
        "observability_event": True,
        "event_type": "retrieval_trace",
        "retrieval": {
            "request_id": trace.request_id,
            "user_id": trace.user_id,
            "model": trace.model_selected,
            "token_budget": trace.token_budget,
            "total_tokens_used": trace.total_tokens_used,
            "retrieval_time_ms": trace.retrieval_time_ms,
            "context_hash": trace.context_hash,
            "error": trace.error,
        },
        "tier_breakdown": trace.tier_breakdown,
        "truncations": trace.truncation_events,
        "items_summary": {
            "total_items": len(trace.items_retrieved),
            "avg_relevance": round(
                sum(item.relevance_score for item in trace.items_retrieved)
                / max(1, len(trace.items_retrieved)),
                3,
            ),
            "max_relevance": max(
                (item.relevance_score for item in trace.items_retrieved), default=0
            ),
            "min_relevance": min(
                (item.relevance_score for item in trace.items_retrieved), default=0
            ),
            "truncated_items": sum(1 for item in trace.items_retrieved if item.truncated),
        },
    }


def log_retrieval_structured(logger: Any, trace: Any) -> None:
    log_data = build_log_data(trace)
    if trace.error:
        logger.error("RETRIEVAL: Error occurred", extra={"retrieval": log_data})
    elif trace.total_tokens_used > trace.token_budget:
        logger.warning("RETRIEVAL: Token budget exceeded", extra={"retrieval": log_data})
    else:
        logger.info("RETRIEVAL: Successful", extra={"retrieval": log_data})


async def log_trace_to_file(config: dict, logger: Any, trace: Any) -> None:
    try:
        log_file = config.get("observability", {}).get("retrieval_log_file", "retrievals.log")

        def _append() -> None:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(trace.to_json() + "\n")

        await asyncio.to_thread(_append)
    except Exception as e:
        logger.error("Failed to log retrieval to file:", error=str(e))
