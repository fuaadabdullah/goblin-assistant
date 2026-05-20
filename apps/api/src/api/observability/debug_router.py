"""
Debug Surfaces Router
Provides endpoints for inspecting the observability data and debugging system behavior
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog

from .decision_logger import decision_logger, DecisionReason
from .memory_logger import memory_promotion_logger, PromotionGate
from .retrieval_tracer import retrieval_tracer, RetrievalTier
from .context_snapshotter import context_snapshotter
from ..ops.security import require_ops_access, require_ops_write_access

logger = structlog.get_logger()

router = APIRouter(prefix="/debug", tags=["debug"])


# Write-Time Decision Endpoints
@router.get("/write/decisions/{conversation_id}")
@require_ops_access("read")
async def get_write_decisions(
    conversation_id: str,
    limit: int = Query(100, description="Number of decisions to return"),
    user_id: Optional[str] = Query(None, description="Filter by user ID")
) -> Dict[str, Any]:
    """Get message-by-message write decisions for a conversation"""
    try:
        decisions = await decision_logger.get_decision_history(
            conversation_id=conversation_id,
            limit=limit,
            user_id=user_id
        )
        
        return {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "decisions": decisions,
            "summary": {
                "total_decisions": len(decisions),
                "embedded_count": len([d for d in decisions if d["embedded"]]),
                "summarized_count": len([d for d in decisions if d["summarized"]]),
                "cached_count": len([d for d in decisions if d["cached"]]),
                "discarded_count": len([d for d in decisions if d["discarded"]]),
                "avg_confidence": round(sum(d["confidence"] for d in decisions) / max(1, len(decisions)), 2)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get write decisions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get write decisions: {str(e)}")


@router.get("/write/decisions/stats")
@require_ops_access("read")
async def get_write_decision_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    time_window_hours: int = Query(24, description="Time window in hours")
) -> Dict[str, Any]:
    """Get write decision statistics for monitoring"""
    try:
        stats = await decision_logger.get_decision_stats(
            user_id=user_id,
            time_window_hours=time_window_hours
        )
        
        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get decision stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get decision stats: {str(e)}")


@router.get("/write/decisions/search")
@require_ops_access("read")
async def search_write_decisions(
    query: str = Query(..., description="Search query"),
    conversation_id: Optional[str] = Query(None, description="Filter by conversation"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    classification_type: Optional[str] = Query(None, description="Filter by classification type"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter")
) -> Dict[str, Any]:
    """Search write decisions with advanced filtering"""
    try:
        results = await decision_logger.search_decisions(
            query=query,
            conversation_id=conversation_id,
            user_id=user_id,
            classification_type=classification_type,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "query": query,
            "filters": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "classification_type": classification_type,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            },
            "results": results,
            "total_results": len(results)
        }
    except Exception as e:
        logger.error(f"Failed to search write decisions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search write decisions: {str(e)}")


# Memory Promotion Endpoints
@router.get("/memory/user/{user_id}")
@require_ops_access("read")
async def get_user_memory(
    user_id: str,
    limit: int = Query(100, description="Number of promotions to return")
) -> Dict[str, Any]:
    """Get long-term memory items for a user with full metadata"""
    try:
        promotions = await memory_promotion_logger.get_promotion_history(
            user_id=user_id,
            limit=limit
        )
        
        # Group by category
        by_category = {}
        for promotion in promotions:
            category = promotion["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(promotion)
        
        return {
            "user_id": user_id,
            "memory_items": promotions,
            "summary": {
                "total_items": len(promotions),
                "promoted_items": len([p for p in promotions if p["promotion_decision"]]),
                "rejected_items": len([p for p in promotions if not p["promotion_decision"]]),
                "categories": list(by_category.keys()),
                "avg_confidence": round(sum(p["confidence_score"] for p in promotions) / max(1, len(promotions)), 2)
            },
            "by_category": {cat: len(items) for cat, items in by_category.items()}
        }
    except Exception as e:
        logger.error(f"Failed to get user memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user memory: {str(e)}")


@router.get("/memory/promotions/stats")
@require_ops_access("read")
async def get_memory_promotion_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    time_window_hours: int = Query(24, description="Time window in hours"),
    category: Optional[str] = Query(None, description="Filter by category")
) -> Dict[str, Any]:
    """Get memory promotion statistics for monitoring"""
    try:
        stats = await memory_promotion_logger.get_promotion_stats(
            user_id=user_id,
            time_window_hours=time_window_hours,
            category=category
        )
        
        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "category": category,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get promotion stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get promotion stats: {str(e)}")


@router.get("/memory/health/{user_id}")
@require_ops_access("read")
async def get_memory_health(
    user_id: str
) -> Dict[str, Any]:
    """Get comprehensive memory health report"""
    try:
        health_report = await memory_promotion_logger.get_memory_health_report(
            user_id=user_id
        )
        
        return health_report
    except Exception as e:
        logger.error(f"Failed to get memory health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory health: {str(e)}")


@router.get("/memory/promotions/search")
@require_ops_access("read")
async def search_memory_promotions(
    query: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    promoted_only: bool = Query(False, description="Only show promoted items"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter")
) -> Dict[str, Any]:
    """Search memory promotions with advanced filtering"""
    try:
        results = await memory_promotion_logger.search_promotions(
            query=query,
            user_id=user_id,
            category=category,
            promoted_only=promoted_only,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "query": query,
            "filters": {
                "user_id": user_id,
                "category": category,
                "promoted_only": promoted_only,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            },
            "results": results,
            "total_results": len(results)
        }
    except Exception as e:
        logger.error(f"Failed to search memory promotions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search memory promotions: {str(e)}")


# Retrieval Trace Endpoints
@router.get("/retrieval/trace/{request_id}")
@require_ops_access("read")
async def get_retrieval_trace(
    request_id: str
) -> Dict[str, Any]:
    """Get full retrieval trace for a specific request"""
    try:
        trace = await retrieval_tracer.get_retrieval_trace(request_id)
        
        if not trace:
            raise HTTPException(status_code=404, detail="Retrieval trace not found")
        
        return trace
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get retrieval trace: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval trace: {str(e)}")


@router.get("/retrieval/history")
@require_ops_access("read")
async def get_retrieval_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    model: Optional[str] = Query(None, description="Filter by model"),
    limit: int = Query(100, description="Number of traces to return")
) -> Dict[str, Any]:
    """Get retrieval history with filtering"""
    try:
        traces = await retrieval_tracer.get_retrieval_history(
            user_id=user_id,
            model=model,
            limit=limit
        )
        
        return {
            "user_id": user_id,
            "model": model,
            "traces": traces,
            "summary": {
                "total_traces": len(traces),
                "avg_retrieval_time": round(sum(t["retrieval_time_ms"] for t in traces) / max(1, len(traces)), 2) if traces else 0,
                "avg_tokens_used": round(sum(t["total_tokens_used"] for t in traces) / max(1, len(traces)), 2) if traces else 0,
                "error_count": len([t for t in traces if t["error"]]),
                "truncation_count": sum(len(t["truncation_events"]) for t in traces)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get retrieval history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval history: {str(e)}")


@router.get("/retrieval/quality/{user_id}")
@require_ops_access("read")
async def get_retrieval_quality(
    user_id: str
) -> Dict[str, Any]:
    """Get comprehensive retrieval quality report"""
    try:
        quality_report = await retrieval_tracer.get_retrieval_quality_report(
            user_id=user_id
        )
        
        return quality_report
    except Exception as e:
        logger.error(f"Failed to get retrieval quality: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval quality: {str(e)}")


@router.get("/retrieval/stats")
@require_ops_access("read")
async def get_retrieval_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    time_window_hours: int = Query(24, description="Time window in hours"),
    model: Optional[str] = Query(None, description="Filter by model")
) -> Dict[str, Any]:
    """Get retrieval statistics for monitoring"""
    try:
        stats = await retrieval_tracer.get_retrieval_stats(
            user_id=user_id,
            time_window_hours=time_window_hours,
            model=model
        )
        
        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "model": model,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get retrieval stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get retrieval stats: {str(e)}")


# Context Assembly Endpoints
@router.get("/context/snapshot/{request_id}")
@require_ops_access("read")
async def get_context_snapshot(
    request_id: str
) -> Dict[str, Any]:
    """Get context assembly snapshot for a specific request"""
    try:
        snapshot = await context_snapshotter.get_context_snapshot(request_id)
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Context snapshot not found")
        
        return snapshot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get context snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get context snapshot: {str(e)}")


@router.get("/context/replay/{request_id}")
@require_ops_access("read")
async def replay_context(
    request_id: str
) -> Dict[str, Any]:
    """Replay context assembly for debugging purposes"""
    try:
        replay_data = await context_snapshotter.replay_context(request_id)
        
        if not replay_data:
            raise HTTPException(status_code=404, detail="Context snapshot not found")
        
        return replay_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replay context: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to replay context: {str(e)}")


@router.get("/context/history")
@require_ops_access("read")
async def get_context_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    model: Optional[str] = Query(None, description="Filter by model"),
    limit: int = Query(100, description="Number of snapshots to return")
) -> Dict[str, Any]:
    """Get context assembly history with filtering"""
    try:
        snapshots = await context_snapshotter.get_context_history(
            user_id=user_id,
            model=model,
            limit=limit
        )
        
        return {
            "user_id": user_id,
            "model": model,
            "snapshots": snapshots,
            "summary": {
                "total_snapshots": len(snapshots),
                "avg_assembly_time": round(sum(s["assembly_time_ms"] for s in snapshots) / max(1, len(snapshots)), 2) if snapshots else 0,
                "avg_tokens_used": round(sum(s["total_tokens"] for s in snapshots) / max(1, len(snapshots)), 2) if snapshots else 0,
                "redaction_count": sum(s["redaction_details"]["items_redacted"] for s in snapshots),
                "error_count": len([s for s in snapshots if s["error"]])
            }
        }
    except Exception as e:
        logger.error(f"Failed to get context history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get context history: {str(e)}")


@router.get("/context/health/{user_id}")
@require_ops_access("read")
async def get_context_health(
    user_id: str
) -> Dict[str, Any]:
    """Get comprehensive context assembly health report"""
    try:
        health_report = await context_snapshotter.get_context_health_report(
            user_id=user_id
        )
        
        return health_report
    except Exception as e:
        logger.error(f"Failed to get context health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get context health: {str(e)}")


# System-wide Debug Endpoints
@router.get("/system/observability/summary")
@require_ops_access("read")
async def get_observability_summary(
    user_id: Optional[str] = Query(None, description="Filter by user ID")
) -> Dict[str, Any]:
    """Get comprehensive observability summary across all systems"""
    try:
        # Get stats from all observability systems
        decision_stats = await decision_logger.get_decision_stats(
            user_id=user_id,
            time_window_hours=24
        )
        
        memory_stats = await memory_promotion_logger.get_promotion_stats(
            user_id=user_id,
            time_window_hours=24
        )
        
        retrieval_stats = await retrieval_tracer.get_retrieval_stats(
            user_id=user_id,
            time_window_hours=24
        )
        
        context_stats = await context_snapshotter.get_context_assembly_stats(
            user_id=user_id,
            time_window_hours=24
        )
        
        return {
            "user_id": user_id,
            "summary": {
                "time_window": "24 hours",
                "decision_system": {
                    "total_decisions": decision_stats.get("total_decisions", 0),
                    "avg_confidence": decision_stats.get("avg_confidence", 0),
                    "outcome_distribution": decision_stats.get("outcome_stats", {})
                },
                "memory_system": {
                    "promotion_attempts": memory_stats.get("total_attempts", 0),
                    "promotion_rate": memory_stats.get("promotion_rate", 0),
                    "gate_analysis": memory_stats.get("gate_analysis", {})
                },
                "retrieval_system": {
                    "total_retrievals": retrieval_stats.get("total_retrievals", 0),
                    "avg_retrieval_time": retrieval_stats.get("performance", {}).get("avg_retrieval_time", 0),
                    "token_utilization": retrieval_stats.get("token_usage", {}).get("avg_token_utilization", 0),
                    "error_rate": retrieval_stats.get("error_rate", 0)
                },
                "context_system": {
                    "total_assemblies": context_stats.get("total_assemblies", 0),
                    "avg_assembly_time": context_stats.get("assembly_stats", {}).get("avg_assembly_time", 0),
                    "avg_token_utilization": context_stats.get("token_stats", {}).get("avg_token_utilization", 0),
                    "redaction_rate": context_stats.get("redaction_stats", {}).get("redaction_rate", 0)
                }
            },
            "detailed_stats": {
                "decisions": decision_stats,
                "memory": memory_stats,
                "retrieval": retrieval_stats,
                "context": context_stats
            }
        }
    except Exception as e:
        logger.error(f"Failed to get observability summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get observability summary: {str(e)}")


@router.get("/system/observability/health")
@require_ops_access("read")
async def get_system_health(
    user_id: Optional[str] = Query(None, description="Filter by user ID")
) -> Dict[str, Any]:
    """Get comprehensive system health report"""
    try:
        # Get health reports from all systems
        memory_health = await memory_promotion_logger.get_memory_health_report(
            user_id=user_id
        )
        
        retrieval_health = await retrieval_tracer.get_retrieval_quality_report(
            user_id=user_id
        )
        
        context_health = await context_snapshotter.get_context_health_report(
            user_id=user_id
        )
        
        # Calculate overall health status
        health_statuses = [
            memory_health.get("health_status", "unknown"),
            retrieval_health.get("quality_status", "unknown"),
            context_health.get("health_status", "unknown")
        ]
        
        # Determine overall status
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
                "context": context_health
            },
            "recommendations": _combine_recommendations([
                memory_health.get("recommendations", []),
                retrieval_health.get("recommendations", []),
                context_health.get("recommendations", [])
            ])
        }
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")


def _combine_recommendations(recommendation_lists: List[List[str]]) -> List[str]:
    """Combine recommendations from multiple systems"""
    all_recommendations = []
    for recommendations in recommendation_lists:
        all_recommendations.extend(recommendations)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_recommendations = []
    for rec in all_recommendations:
        if rec not in seen:
            seen.add(rec)
            unique_recommendations.append(rec)
    
    return unique_recommendations


# Debug Actions (Write Operations)
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
                "snapshot_cache"
            ]
        }
    except Exception as e:
        logger.error(f"Failed to clear observability cache: {e}")
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
            "reset_counters": ["trace_count"]
        }
    except Exception as e:
        logger.error(f"Failed to reset observability counters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset counters: {str(e)}")