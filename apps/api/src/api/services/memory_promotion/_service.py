import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from api.core.contracts import MemoryItemPromotedPayload
from api.observability.events import event_emitter

from ...storage.database import get_db_context
from ...storage.vector_models import MemoryFactModel
from ..embedding_service import (
    EmbeddingProviderUnavailableError,
    EmbeddingService,
)
from ..observability_models import PromotionDecision
from ..observability_service import observability_service
from ..retrieval_service import retrieval_service as _retrieval_singleton
from .extraction import classify_memory_category, extract_memory_candidates
from .finance_gates import FINANCE_CATEGORIES, evaluate_finance_gates
from .gate_evaluation import evaluate_content_quality, evaluate_stability
from .models import PromotionCandidate, PromotionGate, PromotionResult

logger = structlog.get_logger()


class MemoryPromotionService:
    """Promote stable working-memory signals into long-term memory."""

    def __init__(self):
        self.retrieval_service = _retrieval_singleton
        self.embedding_service = EmbeddingService()
        self._promotion_cache = {}
        self._promotion_thresholds = {
            "repetition_count": 2,
            "time_span_days": 1,
            "stability_score_threshold": 0.8,
            "content_quality_threshold": 0.7,
        }

    async def evaluate_promotion_candidate(self, candidate: PromotionCandidate) -> PromotionResult:
        (
            gates_passed,
            gates_failed,
            promoted,
            reason,
        ) = await self._evaluate_candidate_gates(candidate)

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

        self._log_promotion_event(candidate, promoted, reason)

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

    async def _evaluate_candidate_gates(
        self, candidate: PromotionCandidate
    ) -> tuple[List[PromotionGate], List[PromotionGate], bool, str]:
        gates_passed: List[PromotionGate] = []
        gates_failed: List[PromotionGate] = []
        reasons: List[str] = []

        quality_score = evaluate_content_quality(candidate.content)
        if quality_score >= self._promotion_thresholds["content_quality_threshold"]:
            gates_passed.append(PromotionGate.CONTENT_QUALITY)
        else:
            gates_failed.append(PromotionGate.CONTENT_QUALITY)
            reasons.append(f"Content quality too low: {quality_score:.2f}")

        repetition_score = await self._evaluate_repetition(candidate)
        if repetition_score >= self._promotion_thresholds["repetition_count"]:
            gates_passed.append(PromotionGate.REPETITION)
        else:
            gates_failed.append(PromotionGate.REPETITION)
            reasons.append(
                f"Insufficient repetition: {repetition_score}/"
                f"{self._promotion_thresholds['repetition_count']}"
            )

        time_span_days = await self._evaluate_time_span(candidate)
        if time_span_days >= self._promotion_thresholds["time_span_days"]:
            gates_passed.append(PromotionGate.TIME_SPAN)
        else:
            gates_failed.append(PromotionGate.TIME_SPAN)
            reasons.append(
                f"Insufficient time span: {time_span_days} days < "
                f"{self._promotion_thresholds['time_span_days']} days"
            )

        stability_score = evaluate_stability(candidate.content)
        if stability_score >= self._promotion_thresholds["stability_score_threshold"]:
            gates_passed.append(PromotionGate.STABILITY)
        else:
            gates_failed.append(PromotionGate.STABILITY)
            reasons.append(f"Insufficient stability: {stability_score:.2f}")

        if candidate.category in FINANCE_CATEGORIES:
            finance_gates = evaluate_finance_gates(candidate)
            gates_passed.extend(finance_gates["passed"])
            gates_failed.extend(finance_gates["failed"])
            reasons.extend(finance_gates["reasons"])

        promoted = len(gates_passed) >= 3
        reason = "; ".join(reasons) if reasons else "All gates passed"
        return gates_passed, gates_failed, promoted, reason

    def _log_promotion_event(
        self,
        candidate: PromotionCandidate,
        promoted: bool,
        reason: str,
    ) -> None:
        try:
            if promoted:
                observability_service.log_memory_promotion_event(
                    candidate_text=candidate.content,
                    source=candidate.source_type,
                    confidence_score=candidate.confidence,
                    promotion_decision=PromotionDecision.ACCEPTED,
                    # type: ignore[arg-type]
                    rejection_reason=None,
                    user_id=candidate.metadata.get("user_id"),
                    conversation_id=candidate.source_conversation,
                    request_id=candidate.metadata.get("request_id"),
                )
            else:
                observability_service.log_memory_promotion_event(
                    candidate_text=candidate.content,
                    source=candidate.source_type,
                    confidence_score=candidate.confidence,
                    promotion_decision=PromotionDecision.REJECTED,
                    # type: ignore[arg-type]
                    rejection_reason=reason,
                    user_id=candidate.metadata.get("user_id"),
                    conversation_id=candidate.source_conversation,
                    request_id=candidate.metadata.get("request_id"),
                )
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logger.error(
                "Failed to log memory promotion event",
                error=str(exc),
            )

    async def _evaluate_repetition(self, candidate: PromotionCandidate) -> int:
        try:
            similar_facts = await self._find_similar_memory_facts(
                candidate.content,
                candidate.category,
                user_id=candidate.metadata.get("user_id"),
                threshold=0.8,
            )
            conversation_ids = {
                fact.get("conversation_id")
                for fact in similar_facts
                if fact.get("conversation_id") is not None
            }
            return len(conversation_ids)
        except (RuntimeError, TypeError, ValueError) as exc:
            logger.error("Failed to evaluate repetition", error=str(exc))
            return 0

    async def _evaluate_time_span(self, candidate: PromotionCandidate) -> float:
        try:
            similar_facts = await self._find_similar_memory_facts(
                candidate.content,
                candidate.category,
                user_id=candidate.metadata.get("user_id"),
                threshold=0.7,
            )
            return 1.0 if similar_facts else 0.0
        except (RuntimeError, TypeError, ValueError) as exc:
            logger.error("Failed to evaluate time span", error=str(exc))
            return 0.0

    async def _find_similar_memory_facts(
        self,
        content: str,
        category: str,
        user_id: Optional[str] = None,
        threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        del threshold
        try:
            return await self.retrieval_service.retrieve_memory_facts(
                user_id=user_id,
                query=content,
                categories=[category] if category else None,
                k=10,
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            logger.error("Failed to find similar memory facts", error=str(exc))
            return []

    async def _store_memory_fact(
        self,
        candidate: PromotionCandidate,
    ) -> Any:
        try:
            memory_fact_id = uuid.uuid4().hex
            embedding = await self.embedding_service.embed_text(candidate.content)
            if not embedding:
                logger.warning(
                    "Failed to generate embedding for promoted memory fact",
                    category=candidate.category,
                    content_preview=candidate.content[:50],
                )
                return None

            async with get_db_context() as session:
                fact_model: Any = MemoryFactModel(
                    user_id=candidate.metadata.get("user_id"),
                    fact_text=candidate.content,
                    fact_embedding=embedding,
                    category=candidate.category,
                    metadata_={
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
                    fact_id=memory_fact_id,
                    category=candidate.category,
                    content_preview=candidate.content[:50],
                )
                return memory_fact_id
        except EmbeddingProviderUnavailableError as exc:
            logger.error(
                "Failed to generate memory fact embedding",
                error=str(exc),
            )
            return None
        except (RuntimeError, TypeError, ValueError) as exc:
            logger.error("Failed to store memory fact", error=str(exc))
            return None

    async def promote_from_summary(
        self,
        summary_text: str,
        conversation_id: str,
        user_id: Optional[str] = None,
    ) -> List[PromotionResult]:
        candidates = extract_memory_candidates(
            summary_text,
            conversation_id,
            user_id,
        )
        results = []
        for candidate in candidates:
            result = await self.evaluate_promotion_candidate(candidate)
            results.append(result)
        return results

    def _classify_memory_category(self, content: str) -> Optional[str]:
        return classify_memory_category(content)

    def _evaluate_finance_gates(self, candidate: PromotionCandidate) -> Dict[str, Any]:
        return evaluate_finance_gates(candidate)


memory_promotion_service = MemoryPromotionService()
