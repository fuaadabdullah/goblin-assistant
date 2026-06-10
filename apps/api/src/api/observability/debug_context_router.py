"""
Debug endpoints for context assembly snapshots.
"""

from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from ..ops.security import require_ops_access
from .context_snapshotter import context_snapshotter

logger = structlog.get_logger()

router = APIRouter()


@router.get("/context/snapshot/{request_id}")
@require_ops_access("read")
async def get_context_snapshot(request_id: str) -> Dict[str, Any]:
    """Get context assembly snapshot for a specific request"""
    try:
        snapshot = await context_snapshotter.get_context_snapshot(request_id)

        if not snapshot:
            raise HTTPException(status_code=404, detail="Context snapshot not found")

        return snapshot
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get context snapshot:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get context snapshot: {str(e)}")


@router.get("/context/replay/{request_id}")
@require_ops_access("read")
async def replay_context(request_id: str) -> Dict[str, Any]:
    """Replay context assembly for debugging purposes"""
    try:
        replay_data = await context_snapshotter.replay_context(request_id)

        if not replay_data:
            raise HTTPException(status_code=404, detail="Context snapshot not found")

        return replay_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to replay context:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to replay context: {str(e)}")


@router.get("/context/history")
@require_ops_access("read")
async def get_context_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    model: Optional[str] = Query(None, description="Filter by model"),
    limit: int = Query(100, description="Number of snapshots to return"),
) -> Dict[str, Any]:
    """Get context assembly history with filtering"""
    try:
        snapshots = await context_snapshotter.get_context_history(
            user_id=user_id, model=model, limit=limit
        )

        return {
            "user_id": user_id,
            "model": model,
            "snapshots": snapshots,
            "summary": {
                "total_snapshots": len(snapshots),
                "avg_assembly_time": (
                    round(
                        sum(s["assembly_time_ms"] for s in snapshots) / max(1, len(snapshots)),
                        2,
                    )
                    if snapshots
                    else 0
                ),
                "avg_tokens_used": (
                    round(
                        sum(s["total_tokens"] for s in snapshots) / max(1, len(snapshots)),
                        2,
                    )
                    if snapshots
                    else 0
                ),
                "redaction_count": sum(s["redaction_details"]["items_redacted"] for s in snapshots),
                "error_count": len([s for s in snapshots if s["error"]]),
            },
        }
    except Exception as e:
        logger.error("Failed to get context history:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get context history: {str(e)}")


@router.get("/context/health/{user_id}")
@require_ops_access("read")
async def get_context_health(user_id: str) -> Dict[str, Any]:
    """Get comprehensive context assembly health report"""
    try:
        health_report = await context_snapshotter.get_context_health_report(user_id=user_id)
        return health_report
    except Exception as e:
        logger.error("Failed to get context health:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get context health: {str(e)}")
