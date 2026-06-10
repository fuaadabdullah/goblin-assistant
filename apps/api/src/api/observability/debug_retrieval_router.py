"""
Debug endpoints for retrieval traces.
"""

from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from ..ops.security import require_ops_access
from .retrieval_tracer import retrieval_tracer

logger = structlog.get_logger()

router = APIRouter()


@router.get("/retrieval/trace/{request_id}")
@require_ops_access("read")
async def get_retrieval_trace(request_id: str) -> Dict[str, Any]:
    """Get full retrieval trace for a specific request"""
    try:
        trace = await retrieval_tracer.get_retrieval_trace(request_id)

        if not trace:
            from api.services.observability_service import observability_service as _obs

            rec = next((t for t in _obs.retrieval_traces if t.request_id == request_id), None)
            if rec:
                trace = {
                    "request_id": rec.request_id,
                    "user_id": rec.user_id,
                    "model_selected": rec.model_selected,
                    "token_budget": rec.token_budget,
                    "retrieval_items": rec.items_retrieved,
                    "scoring_breakdown": rec.scoring_breakdown,
                    "token_allocation": rec.token_allocation,
                    "timestamp": rec.timestamp,
                }

        if not trace:
            raise HTTPException(status_code=404, detail="Retrieval trace not found")

        return trace
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get retrieval trace:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval trace: {str(e)}")


@router.get("/retrieval/history")
@require_ops_access("read")
async def get_retrieval_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    model: Optional[str] = Query(None, description="Filter by model"),
    limit: int = Query(100, description="Number of traces to return"),
) -> Dict[str, Any]:
    """Get retrieval history with filtering"""
    try:
        traces = await retrieval_tracer.get_retrieval_history(
            user_id=user_id, model=model, limit=limit
        )

        return {
            "user_id": user_id,
            "model": model,
            "traces": traces,
            "summary": {
                "total_traces": len(traces),
                "avg_retrieval_time": (
                    round(
                        sum(t["retrieval_time_ms"] for t in traces) / max(1, len(traces)),
                        2,
                    )
                    if traces
                    else 0
                ),
                "avg_tokens_used": (
                    round(
                        sum(t["total_tokens_used"] for t in traces) / max(1, len(traces)),
                        2,
                    )
                    if traces
                    else 0
                ),
                "error_count": len([t for t in traces if t["error"]]),
                "truncation_count": sum(len(t["truncation_events"]) for t in traces),
            },
        }
    except Exception as e:
        logger.error("Failed to get retrieval history:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval history: {str(e)}")


@router.get("/retrieval/quality/{user_id}")
@require_ops_access("read")
async def get_retrieval_quality(user_id: str) -> Dict[str, Any]:
    """Get comprehensive retrieval quality report"""
    try:
        quality_report = await retrieval_tracer.get_retrieval_quality_report(user_id=user_id)
        return quality_report
    except Exception as e:
        logger.error("Failed to get retrieval quality:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval quality: {str(e)}")


@router.get("/retrieval/stats")
@require_ops_access("read")
async def get_retrieval_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    time_window_hours: int = Query(24, description="Time window in hours"),
    model: Optional[str] = Query(None, description="Filter by model"),
) -> Dict[str, Any]:
    """Get retrieval statistics for monitoring"""
    try:
        stats = await retrieval_tracer.get_retrieval_stats(
            user_id=user_id, time_window_hours=time_window_hours, model=model
        )

        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "model": model,
            "stats": stats,
        }
    except Exception as e:
        logger.error("Failed to get retrieval stats:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval stats: {str(e)}")
