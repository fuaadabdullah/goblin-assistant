"""Department models — the public-facing abstraction over provider internals.

A Department is a functional specialization of the brain. Each department:
- Has a human-readable department_id (e.g. "reasoning", "coding")
- Maps to a chain of (provider_id, model) pairs for fallback
- Carries a quality policy (latency vs cost vs capability)
- Is what users see instead of "Gemini" or "DeepSeek"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple


class DepartmentId(str, Enum):
    """The canonical set of brain departments.

    These are the ONLY identifiers users and clients will see.
    Internal provider IDs never leave this boundary.
    """

    REASONING = "reasoning"
    CODING = "coding"
    CREATIVE = "creative"
    RECALL = "recall"
    TOOL_USE = "tool_use"
    RESEARCH = "research"
    GENERAL = "general"


class DepartmentQualityTier(str, Enum):
    """Quality-of-service tier for a department's provider selection."""

    SPEED = "speed"  # Fastest available — for simple queries
    BALANCED = "balanced"  # Good quality at reasonable latency
    QUALITY = "quality"  # Best possible output — for complex tasks
    ECONOMY = "economy"  # Cheapest acceptable option


@dataclass(frozen=True)
class DepartmentPolicy:
    """Defines how a department selects and falls back between providers.

    Each entry in the provider_chain is a (provider_id, model_name) pair.
    The dispatcher tries them in order, falling back on failure.
    """

    department_id: DepartmentId
    display_name: str
    description: str
    provider_chain: List[Tuple[str, str]]  # [(provider_id, model), ...]
    default_tier: DepartmentQualityTier = DepartmentQualityTier.BALANCED
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_attachments: bool = True
    supports_vision: bool = False
    max_tokens: int = 4096
    temperature_default: float = 0.7

    @property
    def primary_provider(self) -> Tuple[str, str]:
        """Return the first (provider_id, model) in the chain."""
        return self.provider_chain[0] if self.provider_chain else ("", "")

    @property
    def fallback_providers(self) -> List[Tuple[str, str]]:
        """Return all providers after the first (fallback chain)."""
        return self.provider_chain[1:] if len(self.provider_chain) > 1 else []


@dataclass
class DepartmentSelection:
    """Result of classifying a message into a department.

    This is the routing decision passed downstream. It carries:
    - Which department was chosen
    - Why (human-readable reason)
    - The resolved provider/model (internal — not exposed to user)
    - The quality tier selected based on intent/complexity
    """

    department_id: DepartmentId
    reason: str = ""
    resolved_provider: str = ""
    resolved_model: str = ""
    quality_tier: DepartmentQualityTier = DepartmentQualityTier.BALANCED
    fallback_chain: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, str]:
        """Public-facing representation — NO provider/model info."""
        return {
            "department": self.department_id.value,
            "reason": self.reason,
        }


# ── Mapping: intent_label → department_id ──────────────────────────────

# Default mapping from intent classifier labels to departments.
# Maps known intent labels; everything else falls through to GENERAL.
INTENT_TO_DEPARTMENT: Dict[str, DepartmentId] = {
    # Reasoning & analysis
    "reasoning": DepartmentId.REASONING,
    "logic": DepartmentId.REASONING,
    "analysis": DepartmentId.REASONING,
    "planning": DepartmentId.REASONING,
    "math": DepartmentId.REASONING,
    "problem_solving": DepartmentId.REASONING,
    # Coding
    "coding": DepartmentId.CODING,
    "code_generation": DepartmentId.CODING,
    "debugging": DepartmentId.CODING,
    "refactoring": DepartmentId.CODING,
    "code_review": DepartmentId.CODING,
    # Creative
    "creative": DepartmentId.CREATIVE,
    "writing": DepartmentId.CREATIVE,
    "brainstorming": DepartmentId.CREATIVE,
    "content_creation": DepartmentId.CREATIVE,
    # Recall / memory
    "recall": DepartmentId.RECALL,
    "memory": DepartmentId.RECALL,
    "retrieval": DepartmentId.RECALL,
    "context_query": DepartmentId.RECALL,
    # Tool use
    "tool_use": DepartmentId.TOOL_USE,
    "function_calling": DepartmentId.TOOL_USE,
    "action": DepartmentId.TOOL_USE,
    "automation": DepartmentId.TOOL_USE,
    # Research
    "research": DepartmentId.RESEARCH,
    "deep_research": DepartmentId.RESEARCH,
    "investigation": DepartmentId.RESEARCH,
    "synthesis": DepartmentId.RESEARCH,
    "source_verification": DepartmentId.RESEARCH,
}


# ── Complexity → quality tier mapping ──────────────────────────────────


def quality_tier_for_complexity(complexity_score: float) -> DepartmentQualityTier:
    """Map a complexity score (0.0–1.0) to a quality tier."""
    if complexity_score <= 0.2:
        return DepartmentQualityTier.SPEED
    if complexity_score <= 0.4:
        return DepartmentQualityTier.ECONOMY
    if complexity_score <= 0.7:
        return DepartmentQualityTier.BALANCED
    return DepartmentQualityTier.QUALITY
