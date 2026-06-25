from __future__ import annotations

from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy import select

from ..outcome_scorer import outcome_scorer
from .models import FeedbackEvent

logger = structlog.get_logger(__name__)


async def persist_feedback_event(event: FeedbackEvent, *, logger_override=None) -> None:
    """Write a feedback event to the database and domain events."""
    from ...storage.database import get_db
    from ...storage.feedback_models import FeedbackEventModel
    from ...storage.models import DomainEventModel

    _logger = logger_override or logger

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
        _logger.warning("feedback_event_persist_failed", signal=event.signal, error=str(exc))


async def update_message_outcome(
    message_id: str,
    conversation_id: str,
    user_id: str,
    *,
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
    logger_override=None,
) -> None:
    """Upsert message outcome record, incrementing quality_score for the signal."""
    from ...storage.database import get_db
    from ...storage.feedback_models import MessageOutcomeModel

    _logger = logger_override or logger

    try:
        async with get_db() as db:
            stmt = select(MessageOutcomeModel).where(MessageOutcomeModel.message_id == message_id)
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
        _logger.warning(
            "message_outcome_update_failed",
            message_id=message_id,
            error=str(exc),
        )
