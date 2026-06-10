"""
Routing feedback endpoint — POST /routing/feedback

Accepts thumbs-up/down signals from the frontend and applies them to
the bandit router's in-memory state + Supabase routing_events table.
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
    rating: int  # +1 (helpful) or -1 (unhelpful)
    provider_id: Optional[str] = None
    task_type: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_must_be_binary(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError("rating must be 1 or -1")
        return v


class FeedbackResponse(BaseModel):
    ok: bool


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

    # Update Supabase routing_events with the user rating
    _fire_rating_update(body.request_id, body.rating)

    # Apply rating to in-memory bandit state
    if provider_id and task_type:
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
