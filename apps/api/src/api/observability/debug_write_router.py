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
from ..services.memory_core import memory_core_service
from .decision_logger import decision_logger
from .events import event_emitter
from .memory_logger import memory_promotion_logger
from .migration_metrics import migration_metrics

logger = structlog.get_logger()

router = APIRouter()


def _detail_message(prefix: str, error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{prefix}: {message}"
    return f"{prefix}: Request failed"


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
        from api.services.observability_service import observability_service as _obs

        if _obs.write_decisions:
            decisions = []
            for rec in _obs.write_decisions:
                if isinstance(rec, dict):
                    rec_conversation_id = rec.get("conversation_id")
                    rec_user_id = rec.get("user_id")
                    if rec_conversation_id != conversation_id:
                        continue
                    if user_id and rec_user_id != user_id:
                        continue
                    decisions.append(rec)
                else:
                    if rec.conversation_id != conversation_id:
                        continue
                    if user_id and rec.user_id != user_id:
                        continue
                    decisions.append(
                        {
                            "message_id": rec.message_id,
                            "conversation_id": rec.conversation_id,
                            "user_id": rec.user_id,
                            "timestamp": rec.timestamp,
                            "classification": {
                                "type": rec.classified_type,
                                "confidence": rec.confidence,
                                "reason_codes": rec.reason_codes,
                            },
                            "decisions": {
                                "embedded": rec.embedded,
                                "summarized": rec.summarized,
                                "cached": rec.cached,
                                "discarded": rec.discarded,
                            },
                            "confidence": rec.confidence,
                        }
                    )
        else:
            decisions = await decision_logger.get_decision_history(
                conversation_id=conversation_id, limit=limit, user_id=user_id
            )

        return {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "decisions": decisions,
            "summary": {
                "total_decisions": len(decisions),
                "embedded_count": len([d for d in decisions if _decision_flag(d, "embedded")]),
                "summarized_count": len([d for d in decisions if _decision_flag(d, "summarized")]),
                "cached_count": len([d for d in decisions if _decision_flag(d, "cached")]),
                "discarded_count": len([d for d in decisions if _decision_flag(d, "discarded")]),
                "avg_confidence": round(
                    sum(_decision_confidence(d) for d in decisions) / max(1, len(decisions)), 2
                ),
            },
        }
    except Exception as e:
        logger.error("Failed to get write decisions:", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=_detail_message("Failed to get write decisions", e),
        )


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
        raise HTTPException(
            status_code=500, detail=_detail_message("Failed to get decision stats", e)
        )


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
                if isinstance(rec, dict):
                    rec_conversation_id = rec.get("conversation_id")
                    rec_user_id = rec.get("user_id")
                    rec_classified_type = rec.get("classified_type") or rec.get(
                        "classification", {}
                    ).get("type", "unknown")
                    rec_reason_codes = rec.get("reason_codes") or rec.get("classification", {}).get(
                        "reason_codes", []
                    )
                    rec_embedded = rec.get("decisions", {}).get("embedded", False)
                    rec_summarized = rec.get("decisions", {}).get("summarized", False)
                    rec_discarded = rec.get("decisions", {}).get("discarded", False)
                    rec_confidence = rec.get(
                        "confidence", rec.get("classification", {}).get("confidence", 0.0)
                    )
                    rec_timestamp = rec.get("timestamp", "")
                else:
                    rec_conversation_id = rec.conversation_id
                    rec_user_id = rec.user_id
                    rec_classified_type = rec.classified_type
                    rec_reason_codes = rec.reason_codes
                    rec_embedded = rec.embedded
                    rec_summarized = rec.summarized
                    rec_discarded = rec.discarded
                    rec_confidence = rec.confidence
                    rec_timestamp = rec.timestamp

                if _conv and rec_conversation_id != _conv:
                    continue
                if _uid and rec_user_id != _uid:
                    continue
                if _cls and rec_classified_type != _cls:
                    continue
                searchable = f"{rec_classified_type} {' '.join(rec_reason_codes)}"
                if q and q not in searchable.lower():
                    continue
                results.append(
                    {
                        "message_id": rec.get("message_id")
                        if isinstance(rec, dict)
                        else rec.message_id,
                        "conversation_id": rec_conversation_id,
                        "user_id": rec_user_id,
                        "classified_type": rec_classified_type,
                        "embedded": rec_embedded,
                        "summarized": rec_summarized,
                        "discarded": rec_discarded,
                        "confidence": rec_confidence,
                        "reason_codes": rec_reason_codes,
                        "timestamp": rec_timestamp,
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
        raise HTTPException(
            status_code=500,
            detail=_detail_message("Failed to search write decisions", e),
        )


# Memory Promotion Endpoints
@router.get("/memory/user/{user_id}")
@require_ops_access("read")
async def get_user_memory(
    user_id: str, limit: int = Query(100, description="Number of promotions to return")
) -> Dict[str, Any]:
    """Get long-term memory items for a user with full metadata"""
    try:
        memory_items = await memory_core_service.export_user_memory(user_id)
        promotions = await memory_promotion_logger.get_promotion_history(
            user_id=user_id, limit=limit if isinstance(limit, int) else 100
        )

        by_category = {}
        for item in memory_items:
            category = item.get("category") or item.get("type") or "uncategorized"
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(item)

        return {
            "user_id": user_id,
            "memory_items": memory_items,
            "promotion_history": promotions,
            "summary": {
                "total_items": len(memory_items),
                "promoted_items": len([p for p in promotions if p["promotion_decision"]]),
                "rejected_items": len([p for p in promotions if not p["promotion_decision"]]),
                "categories": list(by_category.keys()),
                "avg_confidence": round(
                    sum(float(p.get("confidence", 0.0)) for p in memory_items)
                    / max(1, len(memory_items)),
                    2,
                ),
            },
            "by_category": {cat: len(items) for cat, items in by_category.items()},
        }
    except Exception as e:
        logger.error("Failed to get user memory:", error=str(e))
        raise HTTPException(status_code=500, detail=_detail_message("Failed to get user memory", e))


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
        raise HTTPException(
            status_code=500,
            detail=_detail_message("Failed to get promotion stats", e),
        )


@router.get("/memory/health/{user_id}")
@require_ops_access("read")
async def get_memory_health(user_id: str) -> Dict[str, Any]:
    """Get comprehensive memory health report"""
    try:
        health_report = await memory_promotion_logger.get_memory_health_report(user_id=user_id)
        return health_report
    except Exception as e:
        logger.error("Failed to get memory health:", error=str(e))
        raise HTTPException(
            status_code=500, detail=_detail_message("Failed to get memory health", e)
        )


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
            from api.services.observability_service import observability_service as _obs

            q = query.lower() if isinstance(query, str) else ""
            _uid = user_id if isinstance(user_id, str) else None
            _category = category if isinstance(category, str) else None
            for rec in _obs.memory_promotions:
                if isinstance(rec, dict):
                    rec_user_id = rec.get("user_id")
                    rec_category = rec.get("source")
                    rec_candidate_text = rec.get("candidate_text", "")
                    rec_confidence = rec.get("confidence_score", 0.0)
                    rec_timestamp = rec.get("timestamp", "")
                    rec_conversation_id = rec.get("conversation_id")
                    rec_memory_state = rec.get("memory_state")
                    rec_conflict_reason = rec.get("conflict_reason")
                    rec_conflicting_memory_ids = rec.get("conflicting_memory_ids", [])
                    promotion_decision = rec.get("promotion_decision")
                    rejection_reason = rec.get("rejection_reason")
                else:
                    rec_user_id = rec.user_id
                    rec_category = rec.source
                    rec_candidate_text = rec.candidate_text
                    rec_confidence = rec.confidence_score
                    rec_timestamp = rec.timestamp
                    rec_conversation_id = rec.conversation_id
                    rec_memory_state = rec.memory_state
                    rec_conflict_reason = rec.conflict_reason
                    rec_conflicting_memory_ids = rec.conflicting_memory_ids
                    promotion_decision = rec.promotion_decision
                    rejection_reason = rec.rejection_reason

                if _uid and rec_user_id != _uid:
                    continue
                if _category and rec_category != _category:
                    continue
                if q and q not in rec_candidate_text.lower():
                    continue

                is_promoted = bool(
                    promotion_decision
                    and getattr(promotion_decision, "value", promotion_decision) != "rejected"
                )
                if promoted_only and not is_promoted:
                    continue

                results.append(
                    {
                        "candidate_text": rec_candidate_text,
                        "source": rec_category,
                        "user_id": rec_user_id,
                        "conversation_id": rec_conversation_id,
                        "confidence_score": rec_confidence,
                        "promoted": is_promoted,
                        "promotion_decision": getattr(
                            promotion_decision, "value", promotion_decision
                        ),
                        "rejection_reason": rejection_reason,
                        "memory_state": rec_memory_state,
                        "conflict_reason": rec_conflict_reason,
                        "conflicting_memory_ids": rec_conflicting_memory_ids,
                        "timestamp": rec_timestamp,
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
        raise HTTPException(
            status_code=500,
            detail=_detail_message("Failed to search memory promotions", e),
        )


def _decision_flag(decision: Any, field: str) -> bool:
    if isinstance(decision, dict):
        if field == "embedded":
            return bool(decision.get("decisions", {}).get("embedded", False))
        if field == "summarized":
            return bool(decision.get("decisions", {}).get("summarized", False))
        if field == "cached":
            return bool(decision.get("decisions", {}).get("cached", False))
        if field == "discarded":
            return bool(decision.get("decisions", {}).get("discarded", False))
        return False
    return bool(getattr(decision, field, False))


def _decision_confidence(decision: Any) -> float:
    if isinstance(decision, dict):
        return float(
            decision.get("confidence", decision.get("classification", {}).get("confidence", 0.0))
        )
    return float(getattr(decision, "confidence", 0.0))
