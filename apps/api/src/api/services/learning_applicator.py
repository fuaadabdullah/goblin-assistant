"""Batch processor: implicit feedback signals → routing weight updates.

Runs every 15 minutes via BackgroundTaskManager. Processes feedback_events rows
where applied_to_bandit=False and translates each implicit signal into a
(success, rating) reward, then applies it to the three learned systems:
  - Thompson Sampling bandit (ml_router.bandit_cache)
  - Feature router weights (feature_router.feature_router)
  - User preference profiles (preference_learner)

Explicit ratings (thumbs_up / thumbs_down) are skipped here — POST /routing/feedback
already applies them immediately on every request.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..storage.feedback_models import FeedbackEventModel, MessageOutcomeModel

logger = logging.getLogger(__name__)

# Applied immediately by POST /routing/feedback — skip in batch to avoid double-counting
_SKIP_SIGNALS = frozenset({"thumbs_up", "thumbs_down"})

# Signal → (success, int_rating)
# success True/False → bandit observation_count += 1, alpha or beta += 1
# success None → rating-only, no observation_count change
# int_rating +1/-1 → alpha or beta += 0.5 nudge; None → no nudge
_SIGNAL_REWARD: dict[str, tuple[Optional[bool], Optional[int]]] = {
    "regenerate": (False, -1),  # clear rejection — user tried again
    "delete": (False, -1),  # rejection
    "provider_switch": (False, -1),  # implicit vote against the previous provider
    "copy": (True, +1),  # user found the response useful
    "continue": (True, None),  # conversation kept going — weak positive
    "model_switch": (None, -1),  # rating nudge only, not a hard outcome
}


class LearningApplicator:
    """Batch feedback consumer: translates stored signals into live weight updates."""

    async def apply_batch(self, db: AsyncSession, limit: int = 100) -> int:
        """Process up to `limit` unapplied feedback events.

        Returns the count of rows marked applied.
        """
        rows = await self._fetch_unapplied(db, limit)
        if not rows:
            return 0

        applied_ids: List[str] = []
        for row, quality_score in rows:
            if row.signal in _SKIP_SIGNALS:
                applied_ids.append(row.event_id)
                continue

            reward = _SIGNAL_REWARD.get(row.signal)
            if reward is None:
                # Unknown signal — mark applied so it doesn't block the queue
                applied_ids.append(row.event_id)
                continue

            success, rating = reward
            self._apply_to_bandit(row, success, rating, quality_score)
            self._apply_to_feature_router(row, success, rating)
            self._apply_to_preference(row, rating)
            applied_ids.append(row.event_id)

        if applied_ids:
            await self._mark_applied(db, applied_ids)

        logger.info("learning_applicator_batch_done applied=%d", len(applied_ids))
        return len(applied_ids)

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def _fetch_unapplied(self, db: AsyncSession, limit: int) -> List[Any]:
        """Return (FeedbackEventModel, quality_score | None) tuples.

        LEFT OUTER JOIN with message_outcomes so the batch processor has the
        accumulated quality score without a second round-trip per row.
        """
        stmt = (
            select(
                FeedbackEventModel,
                MessageOutcomeModel.quality_score.label("msg_quality"),
            )
            .outerjoin(
                MessageOutcomeModel,
                FeedbackEventModel.message_id == MessageOutcomeModel.message_id,
            )
            .where(FeedbackEventModel.applied_to_bandit.is_(False))
            .order_by(FeedbackEventModel.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.all()  # List of Row(FeedbackEventModel, quality_score)

    # ── Bandit ────────────────────────────────────────────────────────────────

    def _apply_to_bandit(
        self,
        row: Any,
        success: Optional[bool],
        rating: Optional[int],
        quality_score: Optional[float] = None,
    ) -> None:
        if not row.task_type or not row.provider:
            return
        try:
            from api.routing.ml_router import (  # noqa: PLC0415
                _fire_bandit_state_upsert,
                bandit_cache,
            )

            from .outcome_scorer import outcome_scorer  # noqa: PLC0415

            # When a quality score is available, use a proportional float rating
            # (scaled to ±2) instead of the fixed binary ±1 from _SIGNAL_REWARD.
            # This lets the bandit distinguish a message rated +8 from one rated +2.
            if quality_score is not None:
                rating = round(outcome_scorer.normalize(quality_score) * 2)

            updated = bandit_cache.update(
                row.task_type,
                row.provider,
                success=success,
                rating=rating,
            )
            _fire_bandit_state_upsert(updated)
        except Exception as exc:
            logger.debug("learning_bandit_failed signal=%s error=%s", row.signal, exc)

    # ── Feature router ────────────────────────────────────────────────────────

    def _apply_to_feature_router(
        self,
        row: Any,
        success: Optional[bool],
        rating: Optional[int],
    ) -> None:
        # Feature router needs a hard success/failure — skip rating-only signals
        if success is None or not row.task_type or not row.provider:
            return
        try:
            from api.routing.feature_extractor import (  # noqa: PLC0415
                ProviderFeatures,
                RoutingFeatures,
                feature_extractor,
            )
            from api.routing.feature_router import feature_router  # noqa: PLC0415
            from api.routing.router_registry import registry  # noqa: PLC0415

            # Reconstruct a minimal RoutingFeatures from the stored context fields.
            # The original prompt is gone so we use stored metadata for the key signals.
            request_features = RoutingFeatures(
                prompt_length_bucket=1,  # medium — original not stored
                task_type=row.task_type or "chat",
                complexity_score=float(row.complexity_score or 0.5),
                conversation_turn=0,
                intent_label=row.intent_label or row.task_type or "unknown",
                intent_confidence=0.7,  # assume reasonable — it was used for routing
            )

            snapshot = registry.snapshot()
            pf_map = feature_extractor.extract_providers(
                [row.provider], {row.provider: (0.0, 0.0)}, snapshot
            )
            provider_features = pf_map.get(
                row.provider,
                ProviderFeatures(
                    provider_id=row.provider,
                    success_rate=0.5,
                    norm_latency=0.5,
                    norm_cost=0.5,
                    is_healthy=True,
                ),
            )

            feature_router.record_outcome(
                task_type=row.task_type,
                request=request_features,
                provider_id=row.provider,
                provider_features=provider_features,
                success=success,
                rating=rating,
            )
        except Exception as exc:
            logger.debug("learning_feature_router_failed signal=%s error=%s", row.signal, exc)

    # ── Preference learner ────────────────────────────────────────────────────

    def _apply_to_preference(self, row: Any, rating: Optional[int]) -> None:
        if not row.user_id or not row.provider:
            return
        try:
            from api.services.preference_learner import preference_learner as _pl  # noqa: PLC0415

            task = asyncio.create_task(
                _pl.record_response(
                    user_id=str(row.user_id),
                    provider_id=row.provider,
                    model=row.model,
                    intent_label=row.intent_label or row.task_type or "unknown",
                    completion_tokens=0,
                    explicit_rating=rating,
                )
            )
            task.add_done_callback(lambda _t: None)
        except Exception as exc:
            logger.debug("learning_preference_failed signal=%s error=%s", row.signal, exc)

    # ── Mark applied ──────────────────────────────────────────────────────────

    async def _mark_applied(self, db: AsyncSession, event_ids: List[str]) -> None:
        stmt = (
            update(FeedbackEventModel)
            .where(FeedbackEventModel.event_id.in_(event_ids))
            .values(applied_to_bandit=True, applied_to_router=True, applied_to_profile=True)
        )
        await db.execute(stmt)
        await db.commit()


learning_applicator = LearningApplicator()
