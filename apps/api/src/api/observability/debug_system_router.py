"""
Debug endpoints for system-wide observability, tool traces, and admin actions.
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from ..ops.security import require_ops_access, require_ops_write_access
from .context_snapshotter import context_snapshotter
from .decision_logger import decision_logger
from .memory_logger import memory_promotion_logger
from .retrieval_tracer import retrieval_tracer
from .tool_tracer import tool_tracer

logger = structlog.get_logger()

router = APIRouter()


@router.get("/system/observability/summary")
@require_ops_access("read")
async def get_observability_summary(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
) -> Dict[str, Any]:
    """Get comprehensive observability summary across all systems"""
    try:
        decision_stats = await decision_logger.get_decision_stats(
            user_id=user_id, time_window_hours=24
        )
        memory_stats = await memory_promotion_logger.get_promotion_stats(
            user_id=user_id, time_window_hours=24
        )
        retrieval_stats = await retrieval_tracer.get_retrieval_stats(
            user_id=user_id, time_window_hours=24
        )
        context_stats = await context_snapshotter.get_context_assembly_stats(
            user_id=user_id, time_window_hours=24
        )

        return {
            "user_id": user_id,
            "summary": {
                "time_window": "24 hours",
                "decision_system": {
                    "total_decisions": decision_stats.get("total_decisions", 0),
                    "avg_confidence": decision_stats.get("avg_confidence", 0),
                    "outcome_distribution": decision_stats.get("outcome_stats", {}),
                },
                "memory_system": {
                    "promotion_attempts": memory_stats.get("total_attempts", 0),
                    "promotion_rate": memory_stats.get("promotion_rate", 0),
                    "gate_analysis": memory_stats.get("gate_analysis", {}),
                },
                "retrieval_system": {
                    "total_retrievals": retrieval_stats.get("total_retrievals", 0),
                    "avg_retrieval_time": retrieval_stats.get("performance", {}).get(
                        "avg_retrieval_time", 0
                    ),
                    "token_utilization": retrieval_stats.get("token_usage", {}).get(
                        "avg_token_utilization", 0
                    ),
                    "error_rate": retrieval_stats.get("error_rate", 0),
                },
                "context_system": {
                    "total_assemblies": context_stats.get("total_assemblies", 0),
                    "avg_assembly_time": context_stats.get("assembly_stats", {}).get(
                        "avg_assembly_time", 0
                    ),
                    "avg_token_utilization": context_stats.get("token_stats", {}).get(
                        "avg_token_utilization", 0
                    ),
                    "redaction_rate": context_stats.get("redaction_stats", {}).get(
                        "redaction_rate", 0
                    ),
                },
            },
            "detailed_stats": {
                "decisions": decision_stats,
                "memory": memory_stats,
                "retrieval": retrieval_stats,
                "context": context_stats,
            },
        }
    except Exception as e:
        logger.error("Failed to get observability summary:", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get observability summary: {str(e)}"
        )


@router.get("/system/observability/health")
@require_ops_access("read")
async def get_system_health(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
) -> Dict[str, Any]:
    """Get comprehensive system health report"""
    try:
        memory_health = await memory_promotion_logger.get_memory_health_report(user_id=user_id)
        retrieval_health = await retrieval_tracer.get_retrieval_quality_report(user_id=user_id)
        context_health = await context_snapshotter.get_context_health_report(user_id=user_id)

        health_statuses = [
            memory_health.get("health_status", "unknown"),
            retrieval_health.get("quality_status", "unknown"),
            context_health.get("health_status", "unknown"),
        ]

        if "critical" in health_statuses:
            overall_status = "critical"
        elif "warning" in health_statuses:
            overall_status = "warning"
        elif all(status == "healthy" for status in health_statuses):
            overall_status = "healthy"
        else:
            overall_status = "unknown"

        return {
            "user_id": user_id,
            "overall_health": overall_status,
            "system_health": {
                "memory": memory_health,
                "retrieval": retrieval_health,
                "context": context_health,
            },
            "recommendations": _combine_recommendations(
                [
                    memory_health.get("recommendations", []),
                    retrieval_health.get("recommendations", []),
                    context_health.get("recommendations", []),
                ]
            ),
        }
    except Exception as e:
        logger.error("Failed to get system health:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")


def _combine_recommendations(recommendation_lists: List[List[str]]) -> List[str]:
    """Combine recommendations from multiple systems, deduplicating while preserving order."""
    seen: set = set()
    unique: List[str] = []
    for rec in (r for recs in recommendation_lists for r in recs):
        if rec not in seen:
            seen.add(rec)
            unique.append(rec)
    return unique


@router.post("/system/observability/clear-cache")
@require_ops_write_access()
async def clear_observability_cache() -> Dict[str, Any]:
    """Clear all observability caches for debugging"""
    try:
        decision_logger._decision_cache.clear()
        memory_promotion_logger._promotion_cache.clear()
        retrieval_tracer._trace_cache.clear()
        context_snapshotter._snapshot_cache.clear()

        logger.info("Observability caches cleared")

        return {
            "success": True,
            "message": "All observability caches cleared successfully",
            "cleared_caches": [
                "decision_cache",
                "promotion_cache",
                "retrieval_cache",
                "snapshot_cache",
            ],
        }
    except Exception as e:
        logger.error("Failed to clear observability cache:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.post("/system/observability/reset-counters")
@require_ops_write_access()
async def reset_observability_counters() -> Dict[str, Any]:
    """Reset observability counters for debugging"""
    try:
        retrieval_tracer._trace_count = 0
        logger.info("Observability counters reset")
        return {
            "success": True,
            "message": "Observability counters reset successfully",
            "reset_counters": ["trace_count"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset observability counters: {str(e)}",
        )


@router.get("/tool-trace/{request_id}")
@require_ops_access("read")
async def get_tool_trace(request_id: str) -> Dict[str, Any]:
    """Get full tool execution trace for a specific request"""
    try:
        result = tool_tracer.get_tool_trace(request_id)

        if not result:
            raise HTTPException(status_code=404, detail="Tool trace not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tool trace:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get tool trace: {str(e)}")


@router.get("/tool-trace/conversation/{conversation_id}")
@require_ops_access("read")
async def get_conversation_tool_traces(
    conversation_id: str,
    limit: int = Query(50, description="Results per page"),
    offset: int = Query(0, description="Pagination offset"),
) -> Dict[str, Any]:
    """Get all tool execution traces for a conversation"""
    try:
        result = tool_tracer.get_conversation_tool_traces(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
        )
        return result
    except Exception as e:
        logger.error("Failed to get conversation tool traces:", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation tool traces: {str(e)}",
        )


@router.get("/tool-trace/stats")
@require_ops_access("read")
async def get_tool_trace_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> Dict[str, Any]:
    """Get tool execution statistics for monitoring"""
    try:
        stats = tool_tracer.get_tool_trace_stats(
            user_id=user_id,
            time_window_hours=time_window_hours,
        )
        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "data": stats,
        }
    except Exception as e:
        logger.error("Failed to get tool trace stats:", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tool trace stats: {str(e)}",
        )
