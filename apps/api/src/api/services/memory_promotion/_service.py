from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog

from api.core.contracts import MemoryItemPromotedPayload
from api.observability.events import event_emitter

from ..retrieval_service import retrieval_service as _retrieval_singleton
from ..observability_service import observability_service
from ...storage.vector_models import MemoryFactModel
from ...storage.database import get_db

from .models import PromotionCandidate, PromotionGate, PromotionResult
from .gate_evaluation import evaluate_content_quality, evaluate_stability
from .finance_gates import FINANCE_CATEGORIES, evaluate_finance_gates
from .extraction import extract_memory_candidates

logger = structlog.get_logger()


class MemoryPromotionService:
    """
    Service for promoting information from working memory to long-term memory.

    Core Law: Long-term memory must be boring, stable, and provable.
    """

    def __init__(self):
        self.retrieval_service = _retrieval_singleton
        self._promotion_cache = {}
        self._promotion_thresholds = {
            "repetition_count": 2,
            "time_span_days": 1,
            "stability_score_threshold": 0.8,
            "content_quality_threshold": 0.7,
        }

    async def evaluate_promotion_candidate(self, candidate: PromotionCandidate) -> PromotionResult:
        gates_passed = []
        gates_failed = []
        reasons = []

        # Gate 1: Content Quality
        quality_score = evaluate_content_quality(candidate.content)
        if quality_score >= self._promotion_thresholds["content_quality_threshold"]:
            gates_passed.append(PromotionGate.CONTENT_QUALITY)
        else:
            gates_failed.append(PromotionGate.CONTENT_QUALITY)
            reasons.append(f"Content quality too low: {quality_score:.2f}")

        # Gate 2: Repetition
        repetition_score = await self._evaluate_repetition(candidate)
        if repetition_score >= self._promotion_thresholds["repetition_count"]:
            gates_passed.append(PromotionGate.REPETITION)
        else:
            gates_failed.append(PromotionGate.REPETITION)
            reasons.append(
                f"Insufficient repetition: {repetition_score}/"
                f"{self._promotion_thresholds['repetition_count']}"
            )

        # Gate 3: Time Span
        time_span_days = await self._evaluate_time_span(candidate)
        if time_span_days >= self._promotion_thresholds["time_span_days"]:
            gates_passed.append(PromotionGate.TIME_SPAN)
        else:
            gates_failed.append(PromotionGate.TIME_SPAN)
            reasons.append(
                f"Insufficient time span: {time_span_days} days < "
                f"{self._promotion_thresholds['time_span_days']} days"
            )

        # Gate 4: Stability
        stability_score = evaluate_stability(candidate.content)
        if stability_score >= self._promotion_thresholds["stability_score_threshold"]:
            gates_passed.append(PromotionGate.STABILITY)
        else:
            gates_failed.append(PromotionGate.STABILITY)
            reasons.append(f"Insufficient stability: {stability_score:.2f}")

        # Finance content gets additional gates (non-blocking extras)
        if candidate.category in FINANCE_CATEGORIES:
            finance_gates = evaluate_finance_gates(candidate)
            gates_passed.extend(finance_gates["passed"])
            gates_failed.extend(finance_gates["failed"])
            reasons.extend(finance_gates["reasons"])

        promoted = len(gates_passed) >= 3
        reason = "; ".join(reasons) if reasons else "All gates passed"

        result = PromotionResult(
            promoted=promoted,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            reason=reason,
        )

        logger.info(
            "Memory promotion evaluation",
            content_preview=candidate.content[:50],
            category=candidate.category,
            gates_passed=[gate.value for gate in gates_passed],
            gates_failed=[gate.value for gate in gates_failed],
            promoted=promoted,
        )

        try:
            observability_service.log_memory_promotion_event(
                candidate_text=candidate.content,
                source=candidate.source_type,
                confidence_score=candidate.confidence,
                promotion_decision=result.promoted,
                rejection_reason=reason if not promoted else None,
                user_id=candidate.metadata.get("user_id"),
                conversation_id=candidate.source_conversation,
                request_id=candidate.metadata.get("request_id"),
            )
        except Exception as e:
            logger.error("Failed to log memory promotion event to observability", error=str(e))

        if promoted:
            result.memory_fact_id = await self._store_memory_fact(candidate)
            if result.memory_fact_id:
                await event_emitter.emit(
                    "memory.item.promoted",
                    source="api.services.memory_promotion_service",
                    actor_user_id=candidate.metadata.get("user_id"),
                    correlation_id=candidate.metadata.get("request_id"),
                    payload=MemoryItemPromotedPayload(
                        memory_fact_id=result.memory_fact_id,
                        category=candidate.category,
                        source_conversation=candidate.source_conversation,
                        source_type=candidate.source_type,
                        confidence=candidate.confidence,
                        gates_passed=[gate.value for gate in gates_passed],
                    ),
                )

        return result

    async def _evaluate_repetition(self, candidate: PromotionCandidate) -> int:
        try:
            similar_facts = await self._find_similar_memory_facts(
                candidate.content, candidate.category, threshold=0.8
            )
            return len(set(fact.get("conversation_id") for fact in similar_facts))
        except Exception as e:
            logger.error("Failed to evaluate repetition", error=str(e))
            return 0

    async def _evaluate_time_span(self, candidate: PromotionCandidate) -> float:
        try:
            similar_facts = await self._find_similar_memory_facts(
                candidate.content, candidate.category, threshold=0.7
            )
            if not similar_facts:
                return 0.0
            dates = [fact.get("created_at") for fact in similar_facts if fact.get("created_at")]
            if not dates:
                return 0.0
            time_span = datetime.utcnow() - min(dates)
            return time_span.days
        except Exception as e:
            logger.error("Failed to evaluate time span", error=str(e))
            return 0.0

    async def _find_similar_memory_facts(
        self, content: str, category: str, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        try:
            return await self.retrieval_service.retrieve_memory_facts(
                user_id=None,
                query=content,
                categories=[category] if category else None,
                k=10,
            )
        except Exception as e:
            logger.error("Failed to find similar memory facts", error=str(e))
            return []

    async def _store_memory_fact(self, candidate: PromotionCandidate) -> Optional[str]:
        try:
            async with get_db() as session:
                fact_model = MemoryFactModel(
                    user_id=candidate.metadata.get("user_id"),
                    fact_text=candidate.content,
                    fact_embedding=[],
                    category=candidate.category,
                    metadata={
                        "source_conversation": candidate.source_conversation,
                        "source_type": candidate.source_type,
                        "promotion_confidence": candidate.confidence,
                        "promotion_gates": [gate.value for gate in PromotionGate],
                        "promoted_at": datetime.utcnow().isoformat(),
                    },
                )
                session.add(fact_model)
                await session.commit()
                logger.info(
                    "Memory fact promoted to long-term",
                    fact_id=fact_model.id,
                    category=candidate.category,
                    content_preview=candidate.content[:50],
                )
                return fact_model.id
        except Exception as e:
            logger.error("Failed to store memory fact", error=str(e))
            return None

    async def promote_from_summary(
        self,
        summary_text: str,
        conversation_id: str,
        user_id: Optional[str] = None,
    ) -> List[PromotionResult]:
        candidates = extract_memory_candidates(summary_text, conversation_id, user_id)
        results = []
        for candidate in candidates:
            result = await self.evaluate_promotion_candidate(candidate)
            results.append(result)
        return results


memory_promotion_service = MemoryPromotionService()
