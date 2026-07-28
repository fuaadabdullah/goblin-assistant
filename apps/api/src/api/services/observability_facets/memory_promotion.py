from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

import structlog

from ...observability.memory_logger import MemoryPromotionEvent as ObsMemoryPromotionEvent
from ...observability.memory_logger import PromotionGate, memory_promotion_logger
from ..observability_models import MemoryPromotionEvent, PromotionDecision
from .shared import redact_content

logger = structlog.get_logger()


class MemoryPromotionFacet:
    def __init__(self, owner: Any):
        self._owner = owner

    def log_memory_promotion_event(
        self,
        candidate_text: str,
        source: str,
        confidence_score: float,
        promotion_decision: PromotionDecision,
        rejection_reason: Optional[str],
        user_id: Optional[str],
        conversation_id: Optional[str],
        memory_state: Optional[str] = None,
        conflict_reason: Optional[str] = None,
        conflicting_memory_ids: Optional[List[str]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        try:
            gates_passed = []
            gates_failed = []

            if promotion_decision == PromotionDecision.ACCEPTED:
                gates_passed = [PromotionGate.CONTENT_QUALITY, PromotionGate.STABILITY]
            else:
                gates_failed = [PromotionGate.CONTENT_QUALITY]

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    memory_promotion_logger.log_promotion_attempt(
                        candidate_text=redact_content(candidate_text),
                        category=source,
                        source_conversation=conversation_id or "unknown",
                        source_type=source,
                        confidence_score=confidence_score,
                        promotion_decision=(promotion_decision == PromotionDecision.ACCEPTED),
                        gates_passed=gates_passed,
                        gates_failed=gates_failed,
                        rejection_reason=rejection_reason or conflict_reason,
                        memory_fact_id=None,
                        user_id=user_id,
                        request_id=request_id,
                        metadata={
                            "memory_state": memory_state,
                            "conflict_reason": conflict_reason,
                            "conflicting_memory_ids": list(conflicting_memory_ids or []),
                        },
                    )
                )
            except RuntimeError:
                pass

            event = ObsMemoryPromotionEvent(
                event_id=f"prom_{int(datetime.utcnow().timestamp())}_{hash(candidate_text) % 10000}",
                timestamp=datetime.utcnow(),
                candidate_text=redact_content(candidate_text),
                category=source,
                source_conversation=conversation_id or "unknown",
                source_type=source,
                confidence_score=confidence_score,
                promotion_decision=(promotion_decision == PromotionDecision.ACCEPTED),
                gates_passed=gates_passed,
                gates_failed=gates_failed,
                rejection_reason=rejection_reason or conflict_reason,
                memory_fact_id=None,
                user_id=user_id,
                request_id=request_id,
                metadata={
                    "memory_state": memory_state,
                    "conflict_reason": conflict_reason,
                    "conflicting_memory_ids": list(conflicting_memory_ids or []),
                },
            )
            memory_promotion_logger._promotion_cache[
                f"{event.source_conversation}:{hash(candidate_text) % 10000}"
            ] = event

            logger.info(
                "Memory promotion event logged",
                source=source,
                decision=promotion_decision.value,
                confidence=confidence_score,
            )

            self._owner.memory_promotions.append(
                MemoryPromotionEvent(
                    candidate_text=redact_content(candidate_text),
                    source=source,
                    confidence_score=confidence_score,
                    promotion_decision=promotion_decision,
                    rejection_reason=rejection_reason or conflict_reason,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    timestamp=datetime.utcnow().isoformat(),
                    memory_state=memory_state,
                    conflict_reason=conflict_reason,
                    conflicting_memory_ids=list(conflicting_memory_ids or []),
                    request_id=request_id,
                )
            )
        except Exception as e:
            logger.error("Failed to log memory promotion event", error=str(e))
