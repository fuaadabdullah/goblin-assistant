"""Agent archetype registry.

Each archetype is a named agent persona that handles a family of intents.
Archetypes sit above the department/provider layer — they define WHAT the
agent is, while departments define which providers back it.

Build order is explicit and enforced: general → code_review → research → ForgeTM.
ForgeTM is the finance/trading analyst and is intentionally last.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from api.config.archetypes import (
    CODE_REVIEW_CONTRACT,
    DEEP_RESEARCH_CONTRACT,
    GENERAL_ASSISTANT_CONTRACT,
)
from api.departments.models import DepartmentId
from api.routing.intent_models import IntentLabel


class AgentArchetypeId(str, Enum):
    """Canonical archetype identifiers — what the user sees as a mode."""

    GENERAL_ASSISTANT = "general_assistant"
    CODE_REVIEW = "code_review"
    DEEP_RESEARCH = "deep_research"
    FORGE_TM = "forge_tm"


@dataclass(frozen=True)
class AgentArchetype:
    """Defines a named agent persona.

    Fields:
        archetype_id      — canonical identifier
        display_name      — user-facing name
        description       — one-line capability summary
        primary_intents   — IntentLabels that route here first
        departments       — DepartmentIds this archetype draws from, preference order
        tools_enabled     — tool namespaces available to this archetype
        build_order       — implementation sequence (1 = built first)
        is_available      — False while the archetype is stub-only
    """

    archetype_id: AgentArchetypeId
    display_name: str
    description: str
    primary_intents: List[IntentLabel]
    departments: List[DepartmentId]
    tools_enabled: List[str] = field(default_factory=list)
    build_order: int = 99
    is_available: bool = True

    def to_dict(self) -> Dict[str, object]:
        return {
            "archetype_id": self.archetype_id.value,
            "display_name": self.display_name,
            "description": self.description,
            "primary_intents": [i.value for i in self.primary_intents],
            "departments": [d.value for d in self.departments],
            "tools_enabled": list(self.tools_enabled),
            "build_order": self.build_order,
            "is_available": self.is_available,
        }


# ---------------------------------------------------------------------------
# Registry definition — order here is documentation of build priority
# ---------------------------------------------------------------------------

_ARCHETYPES: Dict[AgentArchetypeId, AgentArchetype] = {
    # ── Phase 1: General assistant ─────────────────────────────────────
    # Handles the broadest surface: creative, reasoning, tool use, business,
    # and anything that doesn't classify into a specialist archetype.
    # CODING intentionally excluded — routed to CODE_REVIEW (build_order=2).
    AgentArchetypeId.GENERAL_ASSISTANT: AgentArchetype(
        archetype_id=AgentArchetypeId.GENERAL_ASSISTANT,
        display_name="General Assistant",
        description="Writing, reasoning, tool use, and general help",
        primary_intents=[
            IntentLabel.CREATIVE,
            IntentLabel.BUSINESS,
            IntentLabel.REASONING,
            IntentLabel.AGENT_TASK,
        ],
        departments=[
            DepartmentId.GENERAL,
            DepartmentId.CREATIVE,
            DepartmentId.REASONING,
            DepartmentId.TOOL_USE,
        ],
        tools_enabled=sorted(GENERAL_ASSISTANT_CONTRACT.required_tool_names),
        build_order=1,
        is_available=True,
    ),

    # ── Phase 2: Code review ───────────────────────────────────────────
    # Handles all coding intents: write, debug, review, refactor.
    # Owns IntentLabel.CODING so high-confidence coding queries auto-promote
    # to CODE_REVIEW mode, activating the tool contract and review addendum.
    # Low-confidence CODING queries fall back to GENERAL_ASSISTANT via the
    # _SPECIALIST_CONFIDENCE_THRESHOLD check in dispatcher.py.
    AgentArchetypeId.CODE_REVIEW: AgentArchetype(
        archetype_id=AgentArchetypeId.CODE_REVIEW,
        display_name="Code Review",
        description="Code writing, debugging, review, and refactoring with full tool access",
        primary_intents=[
            IntentLabel.CODING,
        ],
        departments=[
            DepartmentId.CODING,
            DepartmentId.TOOL_USE,
            DepartmentId.GENERAL,
        ],
        tools_enabled=sorted(CODE_REVIEW_CONTRACT.required_tool_names),
        build_order=2,
        is_available=True,
    ),

    # ── Phase 3: Deep research ─────────────────────────────────────────
    # Handles research, academic synthesis, literature review, and any
    # prompt that needs multi-source context assembly.
    AgentArchetypeId.DEEP_RESEARCH: AgentArchetype(
        archetype_id=AgentArchetypeId.DEEP_RESEARCH,
        display_name="Deep Research",
        description="Academic synthesis, multi-source investigation, and literature review",
        primary_intents=[
            IntentLabel.RESEARCH,
        ],
        departments=[
            DepartmentId.RESEARCH,
            DepartmentId.RECALL,
        ],
        tools_enabled=sorted(DEEP_RESEARCH_CONTRACT.required_tool_names),
        build_order=3,
        is_available=True,
    ),

    # ── Phase 4: ForgeTM — trading analyst ────────────────────────────
    # Finance-domain specialist: market data, portfolio analysis, DCF
    # models, earnings synthesis, and quantitative strategy.
    # Intentionally last in build order — the "fun" one that jumps the
    # queue if you let it. Don't let it jump the queue.
    AgentArchetypeId.FORGE_TM: AgentArchetype(
        archetype_id=AgentArchetypeId.FORGE_TM,
        display_name="ForgeTM",
        description="Market analysis, portfolio review, earnings synthesis, and trading strategy",
        primary_intents=[
            IntentLabel.FINANCE,
        ],
        departments=[
            DepartmentId.REASONING,  # finance is reasoning-heavy by design
            DepartmentId.RESEARCH,
        ],
        tools_enabled=[
            "dcf_calculator",
            "earnings_summarizer",
            "get_earnings",
            "get_financials",
            "get_key_ratios",
            "get_price_history",
            "get_stock_quote",
            "portfolio_analyzer",
            "stock_screener",
            "news_summarizer",
            "web_search",
            "memory_recall",
        ],
        build_order=4,
        is_available=False,  # stub — available once finance tooling is wired
    ),
}


class ArchetypeRegistry:
    """Registry of all agent archetypes.

    Provides lookup by archetype_id and iteration in build order.
    """

    def __init__(self, archetypes: Dict[AgentArchetypeId, AgentArchetype]) -> None:
        self._archetypes = dict(archetypes)
        # pre-compute intent → archetype mapping (first match by build_order wins)
        self._intent_map: Dict[IntentLabel, AgentArchetypeId] = {}
        for archetype in sorted(archetypes.values(), key=lambda a: a.build_order):
            for intent in archetype.primary_intents:
                if intent not in self._intent_map:
                    self._intent_map[intent] = archetype.archetype_id

    def get(self, archetype_id: AgentArchetypeId) -> AgentArchetype:
        return self._archetypes[archetype_id]

    def resolve_intent(self, intent: IntentLabel) -> AgentArchetype:
        """Return the archetype that owns this intent label.

        Falls back to GENERAL_ASSISTANT if no archetype claims the intent.
        """
        archetype_id = self._intent_map.get(intent, AgentArchetypeId.GENERAL_ASSISTANT)
        return self._archetypes[archetype_id]

    def list_available(self) -> List[AgentArchetype]:
        """Return archetypes with is_available=True, sorted by build_order."""
        return sorted(
            (a for a in self._archetypes.values() if a.is_available),
            key=lambda a: a.build_order,
        )

    def list_all(self) -> List[AgentArchetype]:
        """Return all archetypes sorted by build_order."""
        return sorted(self._archetypes.values(), key=lambda a: a.build_order)

    def list_public(self) -> List[Dict[str, object]]:
        """Return public-facing summaries for all available archetypes."""
        return [a.to_dict() for a in self.list_available()]


ARCHETYPE_REGISTRY = ArchetypeRegistry(_ARCHETYPES)

__all__ = [
    "AgentArchetype",
    "AgentArchetypeId",
    "ArchetypeRegistry",
    "ARCHETYPE_REGISTRY",
]
