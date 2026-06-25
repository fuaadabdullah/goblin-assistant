"""
Routing feedback endpoint — POST /routing/feedback

Accepts thumbs-up/down signals from the frontend and applies them to:
1. The bandit router's in-memory state + Supabase routing_events table
2. The feedback_events table for long-term analytics
3. The feature router's learned weights
4. The user's preference profile

See docs/architecture/FEEDBACK_LOOPS.md for the full feedback loop design.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["routing"])


class FeedbackRequest(BaseModel):
    request_id: str
    rating: Optional[int] = None  # +1 (helpful) or -1 (unhelpful); optional for non-rating signals
    signal: Optional[str] = None  # 'thumbs_up', 'thumbs_down', 'copy', 'regenerate', 'delete'
    provider_id: Optional[str] = None
    task_type: Optional[str] = None
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    department: Optional[str] = None
    model: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_must_be_binary(cls, v: int) -> int:
        if v is not None and v not in (1, -1):
            raise ValueError("rating must be 1 or -1 if provided")
        return v


class FeedbackResponse(BaseModel):
    ok: bool


class FeedbackStatsResponse(BaseModel):
    total_events: int = 0
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0
    regenerate_count: int = 0
    delete_count: int = 0
    continue_count: int = 0
    copy_count: int = 0
    provider_switch_count: int = 0
    model_switch_count: int = 0
    thumbs_up_rate: float = 0.0
    by_department: dict = {}
    by_provider: dict = {}
    recent_events: list = []


@router.post("/routing/feedback", response_model=FeedbackResponse)
async def submit_routing_feedback(body: FeedbackRequest) -> FeedbackResponse:
    """
    Record a user's thumbs-up (+1) or thumbs-down (-1) for a routed response.

    The request_id links back to the routing_events row created when the
    provider was selected. If provider_id / task_type are not supplied,
    this endpoint queries Supabase to look them up from the request_id.
    """
    provider_id = body.provider_id
    task_type = body.task_type
    user_id: Optional[str] = None

    # If context is missing, fetch it from routing_events
    if not provider_id or not task_type:
        provider_id, task_type, user_id = await _lookup_routing_event(body.request_id)
    else:
        _, _, user_id = await _lookup_routing_event(body.request_id)

    # Determine signal type
    signal = body.signal or (
        "thumbs_up" if body.rating == 1 else "thumbs_down" if body.rating == -1 else "unknown"
    )

    # Record persistent feedback event for analytics
    if user_id and (body.message_id or body.conversation_id):
        try:
            from api.services.feedback_service import (  # noqa: PLC0415
                FeedbackContext,
                FeedbackSignal,
                feedback_service,
            )

            context = FeedbackContext(
                user_id=str(user_id),
                conversation_id=body.conversation_id or "",
                message_id=body.message_id or "",
                request_id=body.request_id,
                department=body.department,
                provider=provider_id or "",
                model=body.model,
                task_type=task_type or "",
            )

            if (
                signal in (FeedbackSignal.THUMBS_UP, FeedbackSignal.THUMBS_DOWN)
                and body.rating is not None
            ):
                await feedback_service.record_explicit_rating(
                    context=context,
                    rating=body.rating,
                )
            elif signal == FeedbackSignal.COPY:
                await feedback_service.record_copied(context=context)
            elif signal == FeedbackSignal.DELETE:
                await feedback_service.record_delete(context=context)
            elif signal == FeedbackSignal.REGENERATE:
                await feedback_service.record_regenerate(context=context)
        except Exception as exc:
            logger.debug("feedback_event_persist_failed error=%s", exc)

    # Update Supabase routing_events with the user rating (only for rating signals)
    if body.rating is not None:
        _fire_rating_update(body.request_id, body.rating)

    # Apply rating to in-memory bandit state (only for rating signals, not copy/delete)
    if provider_id and task_type and body.rating is not None:
        try:
            from api.routing.ml_router import (  # noqa: PLC0415
                _fire_bandit_state_upsert,
                bandit_cache,
            )

            updated = bandit_cache.update(task_type, provider_id, success=None, rating=body.rating)
            _fire_bandit_state_upsert(updated)
        except Exception as exc:
            logger.debug("bandit_rating_update_failed error=%s", exc)

        # Propagate rating to feature router weight learning
        try:
            from api.routing.feature_router import feature_router  # noqa: PLC0415

            found = feature_router.record_outcome_by_request_id(
                request_id=body.request_id,
                task_type=task_type,
                provider_id=provider_id,
                success=True,  # user is rating — they received a response
                rating=body.rating,
            )
            if not found:
                logger.debug(
                    "feature_router_rating_no_cached_features request_id=%s", body.request_id
                )
        except Exception as exc:
            logger.debug("feature_router_rating_update_failed error=%s", exc)

        # Propagate rating to learned department router
        if body.department:
            _update_learned_dept_router(body.request_id, body.department, body.rating)

        # Update learned user preference profile with the explicit rating
        if user_id:
            try:
                import asyncio as _asyncio  # noqa: PLC0415

                from api.services.preference_learner import (
                    preference_learner as _pl,  # noqa: PLC0415
                )

                _pref_task = _asyncio.create_task(
                    _pl.record_response(
                        user_id=str(user_id),
                        provider_id=provider_id,
                        model=None,
                        intent_label=task_type or "unknown",
                        completion_tokens=0,
                        explicit_rating=body.rating,
                    )
                )
                _pref_task.add_done_callback(lambda _t: None)
            except Exception as exc:
                logger.debug("preference_learner_feedback_update_failed error=%s", exc)

    return FeedbackResponse(ok=True)


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(days: int = 7) -> FeedbackStatsResponse:
    """
    Return aggregated feedback statistics for the last N days.

    Used by the ops dashboard to monitor user satisfaction across
    departments, providers, and signal types.
    """
    try:
        from api.services.feedback_service import feedback_service  # noqa: PLC0415
        from api.storage.database import get_db  # noqa: PLC0415

        async with get_db() as db:
            stats = await feedback_service.get_feedback_stats(db, days=days)
            return FeedbackStatsResponse(
                total_events=stats.total_events,
                thumbs_up_count=stats.thumbs_up_count,
                thumbs_down_count=stats.thumbs_down_count,
                regenerate_count=stats.regenerate_count,
                delete_count=stats.delete_count,
                continue_count=stats.continue_count,
                copy_count=stats.copy_count,
                provider_switch_count=stats.provider_switch_count,
                model_switch_count=stats.model_switch_count,
                thumbs_up_rate=stats.thumbs_up_rate,
                by_department=stats.by_department,
                by_provider=stats.by_provider,
                recent_events=stats.recent_events,
            )
    except Exception as exc:
        logger.warning("feedback_stats_failed error=%s", exc)
        return FeedbackStatsResponse()


async def _lookup_routing_event(request_id: str):
    """Fetch provider_id, task_type, and user_id for a request_id from Supabase."""
    try:
        from api.providers.supabase_events import (  # noqa: PLC0415
            _ENABLED,
            _HEADERS,
            _REST,
            _get_client,
        )

        if not _ENABLED:
            return None, None, None

        resp = await _get_client().get(
            f"{_REST}/routing_events",
            headers={**_HEADERS, "Accept": "application/json"},
            params={
                "select": "provider_id,task_type,user_id",
                "request_id": f"eq.{request_id}",
                "was_selected": "eq.true",
                "limit": "1",
            },
        )
        rows = resp.json() if resp.status_code == 200 else []
        if isinstance(rows, list) and rows:
            row = rows[0]
            return row.get("provider_id"), row.get("task_type"), row.get("user_id")
    except Exception as exc:
        logger.debug("routing_event_lookup_failed request_id=%s error=%s", request_id, exc)

    return None, None, None


def _update_learned_dept_router(request_id: str, department: str, rating: Optional[int]) -> None:
    """Apply a user rating to the learned department router's weight model."""
    try:
        from api.routing.learned_department_router import (  # noqa: PLC0415
            learned_department_router as _ldr,
        )

        found = _ldr.record_outcome_by_request_id(
            request_id=request_id,
            department_id=department,
            success=True,
            rating=rating,
        )
        if not found:
            logger.debug("dept_router_rating_no_cached_features request_id=%s", request_id)
    except Exception as exc:
        logger.debug("dept_router_rating_update_failed error=%s", exc)


def _fire_rating_update(request_id: str, rating: int) -> None:
    try:
        from api.providers.supabase_events import (  # noqa: PLC0415
            _HEADERS,
            _REST,
            _fire,
            _get_client,
        )

        async def _patch() -> None:
            if not _REST:
                return
            try:
                await _get_client().patch(
                    f"{_REST}/routing_events",
                    headers={**_HEADERS, "Prefer": "return=minimal"},
                    params={"request_id": f"eq.{request_id}", "was_selected": "eq.true"},
                    json={"user_rating": rating},
                )
            except Exception as exc:
                logger.debug("routing_event_rating_patch_failed error=%s", exc)

        _fire(_patch())
    except Exception as exc:
        logger.debug("rating_update_fire_failed error=%s", exc)
