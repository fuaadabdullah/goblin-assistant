from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PromotionGate(Enum):
    """Promotion gates that must be passed for memory promotion"""

    REPETITION = "repetition"
    TIME_SPAN = "time_span"
    STABILITY = "stability"
    CONTENT_QUALITY = "content_quality"
    # Finance-specific gates
    ENTITY_PLAUSIBILITY = "entity_plausibility"
    RISK_CONTEXT = "risk_context"
    COMPLIANCE_MARKER = "compliance_marker"


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
