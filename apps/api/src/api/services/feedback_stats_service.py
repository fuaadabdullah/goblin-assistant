"""Route-safe feedback stats query helpers."""

from __future__ import annotations

from api.services.feedback_service import FeedbackStats, feedback_service
from api.storage.database import get_db_context


async def get_feedback_stats(days: int = 7) -> FeedbackStats:
    async with get_db_context() as db:
        return await feedback_service.get_feedback_stats(db, days=days)
