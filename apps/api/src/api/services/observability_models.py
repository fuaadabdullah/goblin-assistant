"""
Data models for the Observability Service.

Enums, dataclasses, and type definitions used by ObservabilityService and
its callers. Extracted here to keep the service module focused on behaviour.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class DecisionReason(Enum):
    """Reason codes for write-time decisions"""

    SHORT_CHAT = "short_chat"
    DECLARATIVE_FACT = "declarative_fact"
    TASK_RESULT = "task_result"
    LOW_SIGNAL = "low_signal"
    SYSTEM_MESSAGE = "system_message"
    NOISE = "noise"
    USER_PREFERENCE = "user_preference"
    CONTEXT_RELEVANT = "context_relevant"


class PromotionDecision(Enum):
    """Memory promotion decisions"""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RetrievalTier(Enum):
    """Retrieval tiers for trace recording"""

    LONG_TERM = "long_term"
    WORKING_MEMORY = "working_memory"
    SEMANTIC = "semantic"
    EPHEMERAL = "ephemeral"


@dataclass
class WriteTimeDecisionRecord:
    """Record of write-time decision for a message"""

    message_id: str
    user_id: Optional[str]
    conversation_id: Optional[str]
    message_content: str
    message_role: str
    classified_type: str
    embedded: bool
    summarized: bool
    cached: bool
    discarded: bool
    reason_codes: List[str]
    confidence: float
    timestamp: str
    request_id: Optional[str] = None


@dataclass
class MemoryPromotionEvent:
    """Record of memory promotion attempt"""

    candidate_text: str
    source: str  # "summary", "task", "direct"
    confidence_score: float
    promotion_decision: PromotionDecision
    rejection_reason: Optional[str]
    user_id: Optional[str]
    conversation_id: Optional[str]
    timestamp: str
    request_id: Optional[str] = None


@dataclass
class RetrievalTrace:
    """Complete retrieval trace for an LLM call"""

    request_id: str
    user_id: Optional[str]
    model_selected: str
    token_budget: int
    items_retrieved: List[Dict[str, Any]]
    scoring_breakdown: Dict[str, Any]
    token_allocation: Dict[str, int]
    timestamp: str


@dataclass
class ContextAssemblySnapshot:
    """Snapshot of context assembly before sending to model"""

    request_id: str
    user_id: Optional[str]
    conversation_id: Optional[str]
    context_hash: str
    redacted_snapshot: Dict[str, Any]
    total_token_usage: int
    assembly_details: Dict[str, Any]
    timestamp: str
