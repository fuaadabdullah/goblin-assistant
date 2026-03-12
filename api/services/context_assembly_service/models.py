"""
Data models for the context assembly pipeline.

ContextLayer  — a single slab of assembled context (system, memory, retrieval, …)
ContextBudget — token‑budget configuration for the five retrieval tiers
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ContextLayer:
    """Represents a layer in the context assembly."""

    name: str
    content: str
    tokens: int
    source_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextBudget:
    """Token budget configuration."""

    total_tokens: int = 8000
    system_tokens: int = 300
    long_term_tokens: int = 300
    working_memory_tokens: int = 700
    semantic_retrieval_tokens: int = 1200
    ephemeral_tokens: int = 5500  # Remaining tokens

    @property
    def available_for_retrieval(self) -> int:
        """Tokens available for semantic retrieval after fixed layers."""
        return self.total_tokens - (
            self.system_tokens + self.long_term_tokens + self.working_memory_tokens
        )
