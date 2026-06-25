"""Shared smart-router types and small helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskType(Enum):
    CHAT = "chat"
    CODE_GENERATION = "code"
    CODE_REVIEW = "code_review"
    REASONING = "reasoning"
    SUMMARIZATION = "summary"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image"
    VISION = "vision"
    TRANSLATION = "translation"


class RoutingStrategy(Enum):
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_FIRST = "quality_first"
    LATENCY_OPTIMIZED = "latency_optimized"
    BALANCED = "balanced"
    LOCAL_FIRST = "local_first"
    ML_BANDIT = "ml_bandit"


@dataclass
class ProviderCost:
    input_cost: float
    output_cost: float

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        return input_tokens / 1000 * self.input_cost + output_tokens / 1000 * self.output_cost


@dataclass
class ProviderSelection:
    provider_id: str
    model: str
    reason: str
    fallback_chain: List[str]
    estimated_cost: float
    expected_latency_ms: float


def last_user_message(messages: Optional[List[Dict[str, Any]]]) -> str:
    """Return the content of the last user-role message, or empty string."""
    if not messages:
        return ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            return content if isinstance(content, str) else ""
    return ""
