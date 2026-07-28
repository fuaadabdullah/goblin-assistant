from __future__ import annotations

from datetime import datetime, timedelta

from .models import FeedbackSignal, FeedbackStats


async def build_feedback_stats(
    db,
    days: int,
    *,
    select_fn,
    func_fn,
    desc_fn,
    logger,
) -> FeedbackStats:
    """Return aggregated feedback stats over the last N days."""
    from ...storage.feedback_models import FeedbackEventModel

    stats = FeedbackStats()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select_fn(
                FeedbackEventModel.signal,
                func_fn.count().label("cnt"),
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

        total_ratings = stats.thumbs_up_count + stats.thumbs_down_count
        stats.thumbs_up_rate = stats.thumbs_up_count / total_ratings if total_ratings > 0 else 0.0

        dept_stmt = (
            select_fn(
                FeedbackEventModel.department,
                FeedbackEventModel.signal,
                func_fn.count().label("cnt"),
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

        prov_stmt = (
            select_fn(
                FeedbackEventModel.provider,
                FeedbackEventModel.signal,
                func_fn.count().label("cnt"),
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

        recent_stmt = (
            select_fn(FeedbackEventModel)
            .where(FeedbackEventModel.created_at >= cutoff)
            .order_by(desc_fn(FeedbackEventModel.created_at))
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
