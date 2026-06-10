"""
Debug endpoints for write-time decisions, memory promotions, and domain events.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from api.core.contracts import (
    EventEnvelope,
    EventLogListResponse,
    EventType,
    JsonObject,
    SuccessEnvelope,
)

from ..ops.security import require_ops_access
from .decision_logger import decision_logger
from .events import event_emitter
from .memory_logger import memory_promotion_logger
from .migration_metrics import migration_metrics

logger = structlog.get_logger()

router = APIRouter()


@router.get("/api/migration-metrics")
@require_ops_access("read")
async def get_api_migration_metrics() -> Dict[str, Any]:
    """Get runtime counters for API compatibility migration progress."""
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "metrics": migration_metrics.snapshot(),
    }


@router.get("/events", response_model=SuccessEnvelope[EventLogListResponse])
@require_ops_access("read")
async def list_domain_events(
    request: Request,
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    actor_user_id: Optional[str] = Query(None, description="Filter by actor user ID"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    source: Optional[str] = Query(None, description="Filter by emitting source"),
    limit: int = Query(100, ge=1, le=500, description="Maximum events to return"),
) -> SuccessEnvelope[EventLogListResponse]:
    events = await event_emitter.list_events(
        event_type=event_type,
        actor_user_id=actor_user_id,
        correlation_id=correlation_id,
        source=source,
        limit=limit,
    )
    return SuccessEnvelope(data=EventLogListResponse(events=events, total=len(events)))


@router.get("/events/{event_id}", response_model=SuccessEnvelope[EventEnvelope[JsonObject]])
@require_ops_access("read")
async def get_domain_event(
    request: Request, event_id: str
) -> SuccessEnvelope[EventEnvelope[JsonObject]]:
    event = await event_emitter.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Domain event not found")
    return SuccessEnvelope(data=event)


# Write-Time Decision Endpoints
@router.get("/write/decisions/{conversation_id}")
@require_ops_access("read")
async def get_write_decisions(
    conversation_id: str,
    limit: int = Query(100, description="Number of decisions to return"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
) -> Dict[str, Any]:
    """Get message-by-message write decisions for a conversation"""
    try:
        decisions = await decision_logger.get_decision_history(
            conversation_id=conversation_id, limit=limit, user_id=user_id
        )

        if not decisions:
            from api.services.observability_service import observability_service as _obs

            _uid = user_id if isinstance(user_id, str) else None
            for rec in _obs.write_decisions:
                if rec.conversation_id != conversation_id:
                    continue
                if _uid and rec.user_id != _uid:
                    continue
                decisions.append(
                    {
                        "message_id": rec.message_id,
                        "conversation_id": rec.conversation_id,
                        "user_id": rec.user_id,
                        "classified_type": rec.classified_type,
                        "embedded": rec.embedded,
                        "summarized": rec.summarized,
                        "cached": rec.cached,
                        "discarded": rec.discarded,
                        "confidence": rec.confidence,
                        "reason_codes": rec.reason_codes,
                        "timestamp": rec.timestamp,
                    }
                )
                if len(decisions) >= limit:
                    break

        return {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "decisions": decisions,
            "summary": {
                "total_decisions": len(decisions),
                "embedded_count": len([d for d in decisions if d["embedded"]]),
                "summarized_count": len([d for d in decisions if d["summarized"]]),
                "cached_count": len([d for d in decisions if d.get("cached", False)]),
                "discarded_count": len([d for d in decisions if d["discarded"]]),
                "avg_confidence": round(
                    sum(d["confidence"] for d in decisions) / max(1, len(decisions)), 2
                ),
            },
        }
    except Exception as e:
        logger.error("Failed to get write decisions:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get write decisions: {str(e)}")


@router.get("/write/decisions/stats")
@require_ops_access("read")
async def get_write_decision_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> Dict[str, Any]:
    """Get write decision statistics for monitoring"""
    try:
        stats = await decision_logger.get_decision_stats(
            user_id=user_id, time_window_hours=time_window_hours
        )

        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "stats": stats,
        }
    except Exception as e:
        logger.error("Failed to get decision stats:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get decision stats: {str(e)}")


@router.get("/write/decisions/search")
@require_ops_access("read")
async def search_write_decisions(
    query: str = Query(..., description="Search query"),
    conversation_id: Optional[str] = Query(None, description="Filter by conversation"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    classification_type: Optional[str] = Query(None, description="Filter by classification type"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
) -> Dict[str, Any]:
    """Search write decisions with advanced filtering"""
    try:
        results = await decision_logger.search_decisions(
            query=query,
            conversation_id=conversation_id,
            user_id=user_id,
            classification_type=classification_type,
            start_time=start_time if isinstance(start_time, datetime) else None,
            end_time=end_time if isinstance(end_time, datetime) else None,
        )

        if not results:
            from api.services.observability_service import observability_service as _obs

            q = query.lower() if isinstance(query, str) else ""
            _conv = conversation_id if isinstance(conversation_id, str) else None
            _uid = user_id if isinstance(user_id, str) else None
            _cls = classification_type if isinstance(classification_type, str) else None
            for rec in _obs.write_decisions:
                if _conv and rec.conversation_id != _conv:
                    continue
                if _uid and rec.user_id != _uid:
                    continue
                if _cls and rec.classified_type != _cls:
                    continue
                searchable = f"{rec.classified_type} {' '.join(rec.reason_codes)}"
                if q and q not in searchable.lower():
                    continue
                results.append(
                    {
                        "message_id": rec.message_id,
                        "conversation_id": rec.conversation_id,
                        "user_id": rec.user_id,
                        "classified_type": rec.classified_type,
                        "embedded": rec.embedded,
                        "summarized": rec.summarized,
                        "discarded": rec.discarded,
                        "confidence": rec.confidence,
                        "reason_codes": rec.reason_codes,
                        "timestamp": rec.timestamp,
                    }
                )

        return {
            "query": query,
            "filters": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "classification_type": classification_type,
                "start_time": start_time.isoformat() if isinstance(start_time, datetime) else None,
                "end_time": end_time.isoformat() if isinstance(end_time, datetime) else None,
            },
            "results": results,
            "total_results": len(results),
        }
    except Exception as e:
        logger.error("Failed to search write decisions:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to search write decisions: {str(e)}")


# Memory Promotion Endpoints
@router.get("/memory/user/{user_id}")
@require_ops_access("read")
async def get_user_memory(
    user_id: str, limit: int = Query(100, description="Number of promotions to return")
) -> Dict[str, Any]:
    """Get long-term memory items for a user with full metadata"""
    try:
        promotions = await memory_promotion_logger.get_promotion_history(
            user_id=user_id, limit=limit if isinstance(limit, int) else 100
        )

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
                "avg_confidence": round(
                    sum(p["confidence_score"] for p in promotions) / max(1, len(promotions)),
                    2,
                ),
            },
            "by_category": {cat: len(items) for cat, items in by_category.items()},
        }
    except Exception as e:
        logger.error("Failed to get user memory:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get user memory: {str(e)}")


@router.get("/memory/promotions/stats")
@require_ops_access("read")
async def get_memory_promotion_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    time_window_hours: int = Query(24, description="Time window in hours"),
    category: Optional[str] = Query(None, description="Filter by category"),
) -> Dict[str, Any]:
    """Get memory promotion statistics for monitoring"""
    try:
        stats = await memory_promotion_logger.get_promotion_stats(
            user_id=user_id, time_window_hours=time_window_hours, category=category
        )

        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "category": category,
            "stats": stats,
        }
    except Exception as e:
        logger.error("Failed to get promotion stats:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get promotion stats: {str(e)}")


@router.get("/memory/health/{user_id}")
@require_ops_access("read")
async def get_memory_health(user_id: str) -> Dict[str, Any]:
    """Get comprehensive memory health report"""
    try:
        health_report = await memory_promotion_logger.get_memory_health_report(user_id=user_id)
        return health_report
    except Exception as e:
        logger.error("Failed to get memory health:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get memory health: {str(e)}")


@router.get("/memory/promotions/search")
@require_ops_access("read")
async def search_memory_promotions(
    query: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    promoted_only: bool = Query(False, description="Only show promoted items"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
) -> Dict[str, Any]:
    """Search memory promotions with advanced filtering"""
    try:
        results = await memory_promotion_logger.search_promotions(
            query=query,
            user_id=user_id,
            category=category,
            promoted_only=promoted_only,
            start_time=start_time if isinstance(start_time, datetime) else None,
            end_time=end_time if isinstance(end_time, datetime) else None,
        )

        if not results:
            from api.services.observability_models import PromotionDecision as _PD  # noqa: N814
            from api.services.observability_service import observability_service as _obs

            q = query.lower() if isinstance(query, str) else ""
            _uid = user_id if isinstance(user_id, str) else None
            _promoted_only = promoted_only if isinstance(promoted_only, bool) else False
            for rec in _obs.memory_promotions:
                if _uid and rec.user_id != _uid:
                    continue
                is_promoted = rec.promotion_decision != _PD.REJECTED
                if _promoted_only and not is_promoted:
                    continue
                if q not in rec.candidate_text.lower():
                    continue
                results.append(
                    {
                        "candidate_text": rec.candidate_text,
                        "source": rec.source,
                        "user_id": rec.user_id,
                        "conversation_id": rec.conversation_id,
                        "confidence_score": rec.confidence_score,
                        "promoted": is_promoted,
                        "promotion_decision": rec.promotion_decision.value
                        if rec.promotion_decision
                        else None,
                        "rejection_reason": rec.rejection_reason,
                        "timestamp": rec.timestamp,
                    }
                )

        return {
            "query": query,
            "filters": {
                "user_id": user_id,
                "category": category,
                "promoted_only": promoted_only,
                "start_time": start_time.isoformat() if isinstance(start_time, datetime) else None,
                "end_time": end_time.isoformat() if isinstance(end_time, datetime) else None,
            },
            "results": results,
            "total_results": len(results),
        }
    except Exception as e:
        logger.error("Failed to search memory promotions:", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to search memory promotions: {str(e)}")
