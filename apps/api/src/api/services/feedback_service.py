"""
Feedback Loop Service — Orchestrates the complete feedback learning cycle.

Closes the loop on every decision GoblinOS makes:
  Prediction → Decision → Outcome → Learning

This service:
1. Records explicit signals (thumbs up/down from POST /routing/feedback)
2. Records implicit signals (regenerate, delete, conversation continued, provider switch)
3. Writes to feedback_events and message_outcomes tables
4. Fires DomainEventModel events for the observability layer
5. Coordinate already-updated in-memory bandit state (done by feedback_router.py)

See docs/architecture/FEEDBACK_LOOPS.md for design rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


# ── Signal Constants ──────────────────────────────────────────────────────


class FeedbackSignal:
    """Canonical feedback signal names."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    REGENERATE = "regenerate"
    DELETE = "delete"
    CONTINUE = "continue"
    PROVIDER_SWITCH = "provider_switch"
    MODEL_SWITCH = "model_switch"
    COPY = "copy"


# ── Data Classes ──────────────────────────────────────────────────────────


@dataclass
class FeedbackContext:
    """Context captured at the time a feedback signal is emitted."""

    user_id: str
    conversation_id: str
    message_id: str
    request_id: Optional[str] = None
    department: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    task_type: Optional[str] = None
    intent_label: Optional[str] = None
    complexity_score: Optional[float] = None
    previous_provider: Optional[str] = None
    previous_model: Optional[str] = None


@dataclass
class FeedbackEvent:
    """A single feedback event ready for recording."""

    signal: str
    rating: Optional[int] = None
    context: Optional[FeedbackContext] = None
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackStats:
    """Aggregated feedback statistics for dashboard."""

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
    by_department: Dict[str, Dict[str, int]] = field(default_factory=dict)
    by_provider: Dict[str, Dict[str, int]] = field(default_factory=dict)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)


# ── Service ───────────────────────────────────────────────────────────────


class FeedbackService:
    """
    Service for recording and querying feedback loop signals.

    All public methods are designed to be fire-and-forget safe:
    they catch all exceptions and never block the hot path.
    """

    # ------------------------------------------------------------------
    # Record explicit feedback (thumbs up/down)
    # ------------------------------------------------------------------

    async def record_explicit_rating(
        self,
        context: FeedbackContext,
        rating: int,
    ) -> None:
        """
        Record an explicit thumbs-up (+1) or thumbs-down (-1) rating.

        This writes a feedback_event row and updates the in-memory
        bandit state (done by caller in feedback_router.py).
        """
        signal = FeedbackSignal.THUMBS_UP if rating == 1 else FeedbackSignal.THUMBS_DOWN
        await self._persist_event(
            FeedbackEvent(
                signal=signal,
                rating=rating,
                context=context,
                weight=1.0,
            )
        )
        await self._update_message_outcome(
            message_id=context.message_id,
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            signal=signal,
        )
        logger.info(
            "feedback_explicit_rating_recorded",
            signal=signal,
            user_id=context.user_id,
            message_id=context.message_id,
            provider=context.provider,
            department=context.department,
        )

    # ------------------------------------------------------------------
    # Record implicit signals
    # ------------------------------------------------------------------

    async def record_regenerate(
        self,
        context: FeedbackContext,
    ) -> None:
        """Record that the user regenerated a response (implicit rejection)."""
        await self._persist_event(
            FeedbackEvent(
                signal=FeedbackSignal.REGENERATE,
                context=context,
                weight=0.8,
            )
        )
        await self._update_message_outcome(
            message_id=context.message_id,
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            was_regenerated=True,
            signal=FeedbackSignal.REGENERATE,
        )
        logger.info(
            "feedback_regenerate_recorded",
            user_id=context.user_id,
            message_id=context.message_id,
        )

    async def record_delete(
        self,
        context: FeedbackContext,
    ) -> None:
        """Record that the user deleted a message."""
        await self._persist_event(
            FeedbackEvent(
                signal=FeedbackSignal.DELETE,
                context=context,
                weight=0.8,
            )
        )
        await self._update_message_outcome(
            message_id=context.message_id,
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            was_deleted=True,
            signal=FeedbackSignal.DELETE,
        )
        logger.info(
            "feedback_delete_recorded",
            user_id=context.user_id,
            message_id=context.message_id,
        )

    async def record_copied(
        self,
        context: FeedbackContext,
    ) -> None:
        """Record that the user copied a response (implicit positive signal)."""
        await self._persist_event(
            FeedbackEvent(
                signal=FeedbackSignal.COPY,
                context=context,
                weight=0.6,
            )
        )
        await self._update_message_outcome(
            message_id=context.message_id,
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            was_copied=True,
            signal=FeedbackSignal.COPY,
        )
        logger.debug(
            "feedback_copy_recorded",
            user_id=context.user_id,
            message_id=context.message_id,
        )

    async def record_conversation_continued(
        self,
        context: FeedbackContext,
        next_message_id: str,
    ) -> None:
        """Record that the conversation continued after an assistant response."""
        await self._persist_event(
            FeedbackEvent(
                signal=FeedbackSignal.CONTINUE,
                context=context,
                weight=0.7,
            )
        )
        await self._update_message_outcome(
            message_id=context.message_id,
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            conversation_continued=True,
            next_message_id=next_message_id,
            signal=FeedbackSignal.CONTINUE,
        )
        logger.debug(
            "feedback_continue_recorded",
            user_id=context.user_id,
            message_id=context.message_id,
            next_message_id=next_message_id,
        )

    async def record_provider_switch(
        self,
        context: FeedbackContext,
        new_provider: str,
        new_model: Optional[str] = None,
    ) -> None:
        """Record that the user switched providers/models before their next message."""
        await self._persist_event(
            FeedbackEvent(
                signal=(
                    FeedbackSignal.PROVIDER_SWITCH
                    if new_provider != context.provider
                    else FeedbackSignal.MODEL_SWITCH
                ),
                context=context,
                weight=0.9,
                metadata={
                    "new_provider": new_provider,
                    "new_model": new_model,
                },
            )
        )
        signal = (
            FeedbackSignal.PROVIDER_SWITCH
            if new_provider != context.provider
            else FeedbackSignal.MODEL_SWITCH
        )
        await self._update_message_outcome(
            message_id=context.message_id,
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            provider_switched_before_next=(new_provider != context.provider),
            model_switched_before_next=(new_model != context.model),
            new_provider=new_provider,
            new_model=new_model,
            signal=signal,
        )
        logger.info(
            "feedback_provider_switch_recorded",
            user_id=context.user_id,
            message_id=context.message_id,
            old_provider=context.provider,
            new_provider=new_provider,
        )

    # ------------------------------------------------------------------
    # Stats / analytics
    # ------------------------------------------------------------------

    async def get_feedback_stats(
        self,
        db: AsyncSession,
        days: int = 7,
    ) -> FeedbackStats:
        """
        Return aggregated feedback stats over the last N days.
        """
        from ..storage.feedback_models import FeedbackEventModel

        stats = FeedbackStats()
        try:
            from datetime import timedelta

            cutoff = datetime.utcnow() - timedelta(days=days)

            # Count by signal type
            stmt = (
                select(
                    FeedbackEventModel.signal,
                    func.count().label("cnt"),
                )
                .where(FeedbackEventModel.created_at >= cutoff)
                .group_by(FeedbackEventModel.signal)
            )

            result = await db.execute(stmt)
            for row in result.all():
                signal = row[0]
                count = row[1]
                stats.total_events += count
                if signal == FeedbackSignal.THUMBS_UP:
                    stats.thumbs_up_count = count
                elif signal == FeedbackSignal.THUMBS_DOWN:
                    stats.thumbs_down_count = count
                elif signal == FeedbackSignal.REGENERATE:
                    stats.regenerate_count = count
                elif signal == FeedbackSignal.DELETE:
                    stats.delete_count = count
                elif signal == FeedbackSignal.CONTINUE:
                    stats.continue_count = count
                elif signal == FeedbackSignal.COPY:
                    stats.copy_count = count
                elif signal == FeedbackSignal.PROVIDER_SWITCH:
                    stats.provider_switch_count = count
                elif signal == FeedbackSignal.MODEL_SWITCH:
                    stats.model_switch_count = count

            # Compute rate
            total_ratings = stats.thumbs_up_count + stats.thumbs_down_count
            stats.thumbs_up_rate = (
                stats.thumbs_up_count / total_ratings if total_ratings > 0 else 0.0
            )

            # Count by department
            dept_stmt = (
                select(
                    FeedbackEventModel.department,
                    FeedbackEventModel.signal,
                    func.count().label("cnt"),
                )
                .where(
                    FeedbackEventModel.created_at >= cutoff,
                    FeedbackEventModel.department.isnot(None),
                )
                .group_by(
                    FeedbackEventModel.department,
                    FeedbackEventModel.signal,
                )
            )
            result = await db.execute(dept_stmt)
            for row in result.all():
                dept = row[0]
                signal = row[1]
                count = row[2]
                if dept not in stats.by_department:
                    stats.by_department[dept] = {"thumbs_up": 0, "thumbs_down": 0, "total": 0}
                if signal == FeedbackSignal.THUMBS_UP:
                    stats.by_department[dept]["thumbs_up"] += count
                elif signal == FeedbackSignal.THUMBS_DOWN:
                    stats.by_department[dept]["thumbs_down"] += count
                stats.by_department[dept]["total"] += count

            # Count by provider
            prov_stmt = (
                select(
                    FeedbackEventModel.provider,
                    FeedbackEventModel.signal,
                    func.count().label("cnt"),
                )
                .where(
                    FeedbackEventModel.created_at >= cutoff,
                    FeedbackEventModel.provider.isnot(None),
                )
                .group_by(
                    FeedbackEventModel.provider,
                    FeedbackEventModel.signal,
                )
            )
            result = await db.execute(prov_stmt)
            for row in result.all():
                prov = row[0]
                signal = row[1]
                count = row[2]
                if prov not in stats.by_provider:
                    stats.by_provider[prov] = {"thumbs_up": 0, "thumbs_down": 0, "total": 0}
                if signal == FeedbackSignal.THUMBS_UP:
                    stats.by_provider[prov]["thumbs_up"] += count
                elif signal == FeedbackSignal.THUMBS_DOWN:
                    stats.by_provider[prov]["thumbs_down"] += count
                stats.by_provider[prov]["total"] += count

            # Recent events
            recent_stmt = (
                select(FeedbackEventModel)
                .where(FeedbackEventModel.created_at >= cutoff)
                .order_by(desc(FeedbackEventModel.created_at))
                .limit(20)
            )
            result = await db.execute(recent_stmt)
            for row in result.scalars().all():
                stats.recent_events.append(
                    {
                        "event_id": row.event_id,
                        "signal": row.signal,
                        "rating": row.rating,
                        "user_id": row.user_id,
                        "department": row.department,
                        "provider": row.provider,
                        "model": row.model,
                        "task_type": row.task_type,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
                )

        except Exception as exc:
            logger.warning("feedback_stats_query_failed", error=str(exc))

        return stats

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    async def _persist_event(self, event: FeedbackEvent) -> None:
        """Write a feedback event to the database and domain events."""
        from ..storage.database import get_db
        from ..storage.feedback_models import FeedbackEventModel
        from ..storage.models import DomainEventModel

        try:
            async with get_db() as db:
                model = FeedbackEventModel(
                    user_id=event.context.user_id,
                    conversation_id=event.context.conversation_id,
                    message_id=event.context.message_id,
                    request_id=event.context.request_id,
                    signal=event.signal,
                    rating=event.rating,
                    department=event.context.department,
                    provider=event.context.provider,
                    model=event.context.model,
                    task_type=event.context.task_type,
                    intent_label=event.context.intent_label,
                    complexity_score=event.context.complexity_score,
                    previous_provider=event.context.previous_provider,
                    previous_model=event.context.previous_model,
                    weight=event.weight,
                    created_at=datetime.utcnow(),
                )
                db.add(model)
                await db.flush()

                # Also write to domain events for observability
                domain_event = DomainEventModel(
                    event_type=f"feedback.{event.signal}",
                    source="feedback_service",
                    actor_user_id=event.context.user_id,
                    correlation_id=event.context.request_id,
                    payload={
                        "feedback_event_id": model.event_id,
                        "signal": event.signal,
                        "rating": event.rating,
                        "message_id": event.context.message_id,
                        "conversation_id": event.context.conversation_id,
                        "department": event.context.department,
                        "provider": event.context.provider,
                        "model": event.context.model,
                        "task_type": event.context.task_type,
                        "weight": event.weight,
                    },
                )
                db.add(domain_event)
                await db.commit()

        except Exception as exc:
            logger.warning(
                "feedback_event_persist_failed",
                signal=event.signal,
                error=str(exc),
            )

    async def _update_message_outcome(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        was_regenerated: bool = False,
        was_deleted: bool = False,
        was_copied: bool = False,
        conversation_continued: bool = False,
        provider_switched_before_next: bool = False,
        model_switched_before_next: bool = False,
        next_message_id: Optional[str] = None,
        new_provider: Optional[str] = None,
        new_model: Optional[str] = None,
        signal: Optional[str] = None,
    ) -> None:
        """Upsert message outcome record, incrementing quality_score for the signal."""
        from ..storage.database import get_db
        from ..storage.feedback_models import MessageOutcomeModel
        from .outcome_scorer import outcome_scorer

        try:
            async with get_db() as db:
                stmt = select(MessageOutcomeModel).where(
                    MessageOutcomeModel.message_id == message_id
                )
                result = await db.execute(stmt)
                outcome = result.scalar_one_or_none()

                quality_delta = outcome_scorer.points_for(signal) if signal else 0

                if outcome:
                    if was_regenerated:
                        outcome.was_regenerated = True
                    if was_deleted:
                        outcome.was_deleted = True
                    if was_copied:
                        outcome.was_copied = True
                    if conversation_continued:
                        outcome.conversation_continued = True
                    if provider_switched_before_next:
                        outcome.provider_switched_before_next = True
                    if model_switched_before_next:
                        outcome.model_switched_before_next = True
                    if next_message_id:
                        outcome.next_message_id = next_message_id
                    if new_provider:
                        outcome.new_provider = new_provider
                    if new_model:
                        outcome.new_model = new_model
                    if quality_delta:
                        outcome.quality_score = (outcome.quality_score or 0.0) + quality_delta
                    outcome.updated_at = datetime.utcnow()
                else:
                    outcome = MessageOutcomeModel(
                        message_id=message_id,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        was_regenerated=was_regenerated,
                        was_deleted=was_deleted,
                        was_copied=was_copied,
                        conversation_continued=conversation_continued,
                        provider_switched_before_next=provider_switched_before_next,
                        model_switched_before_next=model_switched_before_next,
                        next_message_id=next_message_id,
                        new_provider=new_provider,
                        new_model=new_model,
                        quality_score=float(quality_delta),
                    )
                    db.add(outcome)

                await db.commit()

        except Exception as exc:
            logger.warning(
                "message_outcome_update_failed",
                message_id=message_id,
                error=str(exc),
            )


# Module-level singleton
feedback_service = FeedbackService()
