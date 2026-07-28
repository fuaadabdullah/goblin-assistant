from __future__ import annotations

from typing import Optional

import structlog

from .models import FeedbackContext, FeedbackEvent, FeedbackSignal, FeedbackStats
from .persistence import persist_feedback_event, update_message_outcome
from .stats import build_feedback_stats

logger = structlog.get_logger(__name__)


class FeedbackService:
    """Service for recording and querying feedback loop signals."""

    async def _persist_event(self, event: FeedbackEvent) -> None:
        await persist_feedback_event(event, logger_override=logger)

    async def _update_message_outcome(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        **kwargs,
    ) -> None:
        await update_message_outcome(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            logger_override=logger,
            **kwargs,
        )

    async def record_explicit_rating(
        self,
        context: FeedbackContext,
        rating: int,
    ) -> None:
        signal = FeedbackSignal.THUMBS_UP if rating == 1 else FeedbackSignal.THUMBS_DOWN
        await self._persist_event(
            FeedbackEvent(
                signal=signal,
                rating=rating,
                context=context,
                weight=1.0,
            ),
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

    async def record_regenerate(self, context: FeedbackContext) -> None:
        await self._persist_event(
            FeedbackEvent(
                signal=FeedbackSignal.REGENERATE,
                context=context,
                weight=0.8,
            ),
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

    async def record_delete(self, context: FeedbackContext) -> None:
        await self._persist_event(
            FeedbackEvent(
                signal=FeedbackSignal.DELETE,
                context=context,
                weight=0.8,
            ),
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

    async def record_copied(self, context: FeedbackContext) -> None:
        await self._persist_event(
            FeedbackEvent(
                signal=FeedbackSignal.COPY,
                context=context,
                weight=0.6,
            ),
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
        await self._persist_event(
            FeedbackEvent(
                signal=FeedbackSignal.CONTINUE,
                context=context,
                weight=0.7,
            ),
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
        signal = (
            FeedbackSignal.PROVIDER_SWITCH
            if new_provider != context.provider
            else FeedbackSignal.MODEL_SWITCH
        )
        await self._persist_event(
            FeedbackEvent(
                signal=signal,
                context=context,
                weight=0.9,
                metadata={
                    "new_provider": new_provider,
                    "new_model": new_model,
                },
            ),
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

    async def get_feedback_stats(self, db, days: int = 7) -> FeedbackStats:
        from .. import feedback_service as facade

        return await build_feedback_stats(
            db,
            days,
            select_fn=facade.select,
            func_fn=facade.func,
            desc_fn=facade.desc,
            logger=logger,
        )


feedback_service = FeedbackService()
