"""
Memory Promotion Service
Implements strict rules for promoting information from working memory to long-term memory
Ensures long-term memory stays boring, stable, and provable
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import structlog

from .message_classifier import MessageType, MessageClassification
from .retrieval_service import RetrievalService
from .cache_service import cache_service
from .observability_service import observability_service
from ..storage.vector_models import MemoryFactModel
from ..storage.database import get_db

logger = structlog.get_logger()


class PromotionGate(Enum):
    """Promotion gates that must be passed for memory promotion"""
    REPETITION = "repetition"
    TIME_SPAN = "time_span"
    STABILITY = "stability"
    CONTENT_QUALITY = "content_quality"


@dataclass
class PromotionCandidate:
    """Candidate for memory promotion"""
    content: str
    category: str
    source_conversation: str
    source_type: str
    confidence: float
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class PromotionResult:
    """Result of memory promotion attempt"""
    promoted: bool
    gates_passed: List[PromotionGate]
    gates_failed: List[PromotionGate]
    reason: str
    memory_fact_id: Optional[str] = None


class MemoryPromotionService:
    """
    Service for promoting information from working memory to long-term memory
    
    Core Law: Long-term memory must be boring, stable, and provable.
    
    What Is Eligible for Promotion:
    1. Preferences (communication style, tooling choices, model preferences, privacy stance)
    2. Facts (ongoing projects, roles, constraints, known objectives)
    3. Identity Traits (rare, high bar - must appear repeatedly)
    
    What Is Never Promoted:
    - Emotions, one-off opinions, temporary goals, complaints, jokes, vents, hypotheticals
    """
    
    def __init__(self):
        self.retrieval_service = RetrievalService()
        self._promotion_cache = {}  # In-memory cache for promotion decisions
        self._promotion_thresholds = {
            "repetition_count": 2,
            "time_span_days": 1,  # Must span at least 1 day
            "stability_score_threshold": 0.8,
            "content_quality_threshold": 0.7
        }
    
    async def evaluate_promotion_candidate(
        self, 
        candidate: PromotionCandidate
    ) -> PromotionResult:
        """
        Evaluate a candidate for memory promotion
        
        Args:
            candidate: Promotion candidate to evaluate
            
        Returns:
            PromotionResult with gates passed/failed
        """
        gates_passed = []
        gates_failed = []
        reasons = []
        
        # Gate 1: Content Quality
        content_quality_score = self._evaluate_content_quality(candidate.content)
        if content_quality_score >= self._promotion_thresholds["content_quality_threshold"]:
            gates_passed.append(PromotionGate.CONTENT_QUALITY)
        else:
            gates_failed.append(PromotionGate.CONTENT_QUALITY)
            reasons.append(f"Content quality too low: {content_quality_score:.2f}")
        
        # Gate 2: Repetition
        repetition_score = await self._evaluate_repetition(candidate)
        if repetition_score >= self._promotion_thresholds["repetition_count"]:
            gates_passed.append(PromotionGate.REPETITION)
        else:
            gates_failed.append(PromotionGate.REPETITION)
            reasons.append(f"Insufficient repetition: {repetition_score}/{self._promotion_thresholds['repetition_count']}")
        
        # Gate 3: Time Span
        time_span_days = await self._evaluate_time_span(candidate)
        if time_span_days >= self._promotion_thresholds["time_span_days"]:
            gates_passed.append(PromotionGate.TIME_SPAN)
        else:
            gates_failed.append(PromotionGate.TIME_SPAN)
            reasons.append(f"Insufficient time span: {time_span_days} days < {self._promotion_thresholds['time_span_days']} days")
        
        # Gate 4: Stability
        stability_score = self._evaluate_stability(candidate.content)
        if stability_score >= self._promotion_thresholds["stability_score_threshold"]:
            gates_passed.append(PromotionGate.STABILITY)
        else:
            gates_failed.append(PromotionGate.STABILITY)
            reasons.append(f"Insufficient stability: {stability_score:.2f}")
        
        # Determine if promotion should occur
        promotion_threshold = 3  # Must pass at least 3 gates
        promoted = len(gates_passed) >= promotion_threshold
        
        reason = "; ".join(reasons) if reasons else "All gates passed"
        
        result = PromotionResult(
            promoted=promoted,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            reason=reason
        )
        
        # Log the decision
        logger.info(
            "Memory promotion evaluation",
            content_preview=candidate.content[:50],
            category=candidate.category,
            gates_passed=[gate.value for gate in gates_passed],
            gates_failed=[gate.value for gate in gates_failed],
            promoted=promoted
        )
        
        # Log promotion event to observability system
        try:
            observability_service.log_memory_promotion_event(
                candidate_text=candidate.content,
                source=candidate.source_type,
                confidence_score=candidate.confidence,
                promotion_decision=result.promoted,
                rejection_reason=reason if not promoted else None,
                user_id=candidate.metadata.get("user_id"),
                conversation_id=candidate.source_conversation,
                request_id=candidate.metadata.get("request_id")
            )
        except Exception as e:
            logger.error("Failed to log memory promotion event to observability", error=str(e))
        
        # If promoted, store the memory fact
        if promoted:
            result.memory_fact_id = await self._store_memory_fact(candidate)
        
        return result
    
    def _evaluate_content_quality(self, content: str) -> float:
        """
        Evaluate content quality based on strict criteria
        
        Rejects:
        - Emotional language
        - One-off opinions
        - Temporary goals
        - Complaints
        - Jokes
        - Vents
        - Hypotheticals
        - Conditional statements
        """
        content_lower = content.lower().strip()
        
        # Penalize emotional language
        emotional_patterns = [
            r"\b(feeling|frustrated|stressed|excited|angry|happy|sad|tired)\b",
            r"\b(right now|today|this week|currently)\b",  # Temporal indicators
            r"\b(i think|i believe|i feel)\b",  # Subjective statements
            r"\b(should|must|have to|need to)\b",  # Imperative/obligatory
            r"\b(lol|lolz|lmao|rofl|=|>#)\b",  # Emojis and laughter
            r"\b(joke|funny|hilarious|silly)\b",  # Humor indicators
            r"\b(complain|complaining|annoyed|pissed|mad)\b",  # Complaints
            r"\b(if|when|maybe|perhaps|possibly)\b",  # Hypotheticals
            r"\b(would|could|should|might)\b",  # Conditionals
        ]
        
        emotional_score = 0
        for pattern in emotional_patterns:
            if re.search(pattern, content_lower):
                emotional_score += 0.2
        
        # Penalize short, vague content
        if len(content) < 20:
            emotional_score += 0.3
        
        # Penalize questions
        if content.endswith("?"):
            emotional_score += 0.2
        
        # Penalize exclamations
        if "!" in content:
            emotional_score += 0.1
        
        # Normalize score (0.0 = perfect, 1.0 = terrible)
        quality_score = min(emotional_score, 1.0)
        
        # Invert for quality score (higher is better)
        return 1.0 - quality_score
    
    async def _evaluate_repetition(self, candidate: PromotionCandidate) -> int:
        """
        Evaluate repetition by checking for similar content in other conversations
        """
        try:
            # Use semantic search to find similar content
            similar_facts = await self._find_similar_memory_facts(
                candidate.content, 
                candidate.category,
                threshold=0.8  # High similarity threshold
            )
            
            # Count distinct conversations
            conversation_count = len(set(fact.get("conversation_id") for fact in similar_facts))
            
            return conversation_count
            
        except Exception as e:
            logger.error("Failed to evaluate repetition", error=str(e))
            return 0
    
    async def _evaluate_time_span(self, candidate: PromotionCandidate) -> float:
        """
        Evaluate time span by checking when similar content first appeared
        """
        try:
            similar_facts = await self._find_similar_memory_facts(
                candidate.content,
                candidate.category,
                threshold=0.7
            )
            
            if not similar_facts:
                return 0.0
            
            # Get earliest creation date
            dates = [fact.get("created_at") for fact in similar_facts if fact.get("created_at")]
            if not dates:
                return 0.0
            
            earliest_date = min(dates)
            time_span = datetime.utcnow() - earliest_date
            return time_span.days
            
        except Exception as e:
            logger.error("Failed to evaluate time span", error=str(e))
            return 0.0
    
    def _evaluate_stability(self, content: str) -> float:
        """
        Evaluate stability based on declarative vs emotional language
        """
        content_lower = content.lower().strip()
        
        # Score based on declarative language
        declarative_patterns = [
            r"\b(i am|i have|i work|i use|i prefer|i need)\b",  # Declarative statements
            r"\b(always|never|consistently|regularly)\b",  # Stable adverbs
            r"\b(prefer|like|use|work|build|develop)\b",  # Stable preferences
        ]
        
        # Score based on objective language
        objective_patterns = [
            r"\b(project|system|tool|framework|language|technology)\b",
            r"\b(requirement|constraint|objective|goal)\b",
            r"\b(prefer|choice|option|alternative)\b",
        ]
        
        stability_score = 0.0
        
        # Check declarative patterns
        for pattern in declarative_patterns:
            if re.search(pattern, content_lower):
                stability_score += 0.2
        
        # Check objective patterns
        for pattern in objective_patterns:
            if re.search(pattern, content_lower):
                stability_score += 0.1
        
        # Penalize emotional/volatile language
        volatile_patterns = [
            r"\b(stressed|frustrated|excited|angry|today|right now)\b",
            r"\b(should|must|have to)\b",
            r"\b(complain|annoyed|mad)\b",
        ]
        
        for pattern in volatile_patterns:
            if re.search(pattern, content_lower):
                stability_score -= 0.3
        
        return max(0.0, min(1.0, stability_score))
    
    async def _find_similar_memory_facts(
        self, 
        content: str, 
        category: str, 
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find similar memory facts for repetition evaluation"""
        try:
            # Use retrieval service to find similar facts
            similar_facts = await self.retrieval_service.retrieve_memory_facts(
                user_id=None,  # Search all users for repetition
                query=content,
                categories=[category] if category else None,
                k=10
            )
            
            return similar_facts
            
        except Exception as e:
            logger.error("Failed to find similar memory facts", error=str(e))
            return []
    
    async def _store_memory_fact(self, candidate: PromotionCandidate) -> Optional[str]:
        """Store a memory fact in long-term memory"""
        try:
            async with get_db() as session:
                fact_model = MemoryFactModel(
                    user_id=candidate.metadata.get("user_id"),
                    fact_text=candidate.content,
                    fact_embedding=[],  # Will be populated by embedding worker
                    category=candidate.category,
                    metadata={
                        "source_conversation": candidate.source_conversation,
                        "source_type": candidate.source_type,
                        "promotion_confidence": candidate.confidence,
                        "promotion_gates": [gate.value for gate in PromotionGate],
                        "promoted_at": datetime.utcnow().isoformat()
                    }
                )
                session.add(fact_model)
                await session.commit()
                
                logger.info(
                    "Memory fact promoted to long-term",
                    fact_id=fact_model.id,
                    category=candidate.category,
                    content_preview=candidate.content[:50]
                )
                
                return fact_model.id
                
        except Exception as e:
            logger.error("Failed to store memory fact", error=str(e))
            return None
    
    async def promote_from_summary(
        self, 
        summary_text: str, 
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> List[PromotionResult]:
        """
        Promote eligible information from conversation summaries
        
        Args:
            summary_text: Summary text to analyze for promotion candidates
            conversation_id: Source conversation ID
            user_id: User ID for the memory
            
        Returns:
            List of promotion results
        """
        results = []
        
        # Extract potential memory candidates from summary
        candidates = self._extract_memory_candidates(summary_text, conversation_id, user_id)
        
        for candidate in candidates:
            result = await self.evaluate_promotion_candidate(candidate)
            results.append(result)
        
        return results
    
    def _extract_memory_candidates(
        self, 
        summary_text: str, 
        conversation_id: str,
        user_id: Optional[str]
    ) -> List[PromotionCandidate]:
        """
        Extract potential memory candidates from summary text
        
        Focuses on:
        1. Preferences (communication style, tooling choices, model preferences, privacy stance)
        2. Facts (ongoing projects, roles, constraints, known objectives)
        3. Identity Traits (rare, high bar)
        """
        candidates = []
        
        # Split summary into sentences
        sentences = re.split(r'[.!?]+', summary_text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Classify the sentence
            category = self._classify_memory_category(sentence)
            if category:
                candidate = PromotionCandidate(
                    content=sentence,
                    category=category,
                    source_conversation=conversation_id,
                    source_type="summary",
                    confidence=0.8,  # Default confidence for summary content
                    metadata={"user_id": user_id},
                    created_at=datetime.utcnow()
                )
                candidates.append(candidate)
        
        return candidates
    
    def _classify_memory_category(self, content: str) -> Optional[str]:
        """
        Classify content into memory categories
        
        Returns category if eligible for long-term memory, None otherwise
        """
        content_lower = content.lower().strip()
        
        # Preferences
        preference_patterns = [
            r"\b(i prefer|i like|i love|i always use|i consistently use)\b",
            r"\b(communication|style|tooling|model|privacy|security)\b",
            r"\b(concise|detailed|technical|simple|clear)\b",
        ]
        
        # Facts
        fact_patterns = [
            r"\b(project|system|role|constraint|objective|goal|requirement)\b",
            r"\b(building|developing|working on|maintaining)\b",
            r"\b(team|company|organization|client)\b",
        ]
        
        # Identity traits (very high bar)
        identity_patterns = [
            r"\b(values|principles|beliefs|philosophy|approach)\b",
            r"\b(rigorous|thorough|methodical|systematic)\b",
        ]
        
        # Check if content contains emotional/temporary language (disqualify)
        emotional_patterns = [
            r"\b(feeling|stressed|frustrated|excited|today|right now|currently)\b",
            r"\b(i think|i believe|i feel)\b",
            r"\b(should|must|have to|need to)\b",
            r"\b(lol|joke|funny|complain|annoyed)\b",
        ]
        
        # Disqualify emotional content
        for pattern in emotional_patterns:
            if re.search(pattern, content_lower):
                return None
        
        # Classify into categories
        for pattern in preference_patterns:
            if re.search(pattern, content_lower):
                return "preference"
        
        for pattern in fact_patterns:
            if re.search(pattern, content_lower):
                return "fact"
        
        for pattern in identity_patterns:
            if re.search(pattern, content_lower):
                return "identity_trait"
        
        return None


# Global memory promotion service instance
memory_promotion_service = MemoryPromotionService()