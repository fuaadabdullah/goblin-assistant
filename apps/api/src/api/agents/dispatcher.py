"""Intent dispatcher — routes a classified intent to an agent archetype.

The dispatcher is the seam between the intent classifier (which label is this?)
and the archetype registry (which agent handles this label?). It also resolves
confidence thresholds and applies fallback logic so callers always get a result.

Usage:
    from api.agents import intent_dispatcher
    from api.routing.intent_classifier import intent_classifier

    intent = intent_classifier.classify(user_message)
    selection = intent_dispatcher.dispatch(intent)
    # selection.archetype is the resolved AgentArchetype
    # selection.fell_back is True when confidence was too low and we used GENERAL
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from api.routing.intent_models import IntentLabel, IntentResult

from .archetypes import (
    ARCHETYPE_REGISTRY,
    AgentArchetype,
    AgentArchetypeId,
)

logger = structlog.get_logger()

# Minimum confidence required to route to a specialist archetype.
# Below this threshold the dispatcher falls back to GENERAL_ASSISTANT.
_SPECIALIST_CONFIDENCE_THRESHOLD = 0.45


@dataclass
class ArchetypeSelection:
    """Result of dispatching an intent to an archetype."""

    archetype: AgentArchetype
    intent: IntentResult
    fell_back: bool = False
    fallback_reason: str = ""

    def to_dict(self) -> dict:
        """Serialize selection for inclusion in request metadata and intent_meta."""
        return {
            "archetype_id": self.archetype.archetype_id.value,
            "archetype_name": self.archetype.display_name,
            "intent_label": self.intent.label.value,
            "intent_confidence": self.intent.confidence,
            "intent_method": self.intent.method,
            "fell_back": self.fell_back,
            "fallback_reason": self.fallback_reason,
            # Load-bearing for ceiling filter in router.py: restricts which
            # tool schemas are sent to the model for this archetype.
            "tools_enabled": list(self.archetype.tools_enabled),
        }


class IntentDispatcher:
    """Routes an IntentResult to the appropriate AgentArchetype.

    Rules (in order):
    1. If the resolved archetype is unavailable (is_available=False), fall back
       to GENERAL_ASSISTANT regardless of confidence.
    2. If confidence < threshold and the intent is not owned by GENERAL_ASSISTANT,
       fall back to GENERAL_ASSISTANT.
    3. Otherwise, return the archetype that owns the intent.
    """

    def dispatch(self, intent: IntentResult) -> ArchetypeSelection:
        """Dispatch a classified intent to an archetype. Never raises."""
        try:
            return self._dispatch(intent)
        except Exception as exc:  # dispatch must never propagate; fallback is load-bearing
            logger.warning(
                "archetype_dispatch_failed",
                intent=intent.label.value,
                error=str(exc),
            )
            general = ARCHETYPE_REGISTRY.get(AgentArchetypeId.GENERAL_ASSISTANT)
            return ArchetypeSelection(
                archetype=general,
                intent=intent,
                fell_back=True,
                fallback_reason=f"dispatch_error: {exc}",
            )

    def _dispatch(self, intent: IntentResult) -> ArchetypeSelection:
        resolved = ARCHETYPE_REGISTRY.resolve_intent(intent.label)

        # Rule 1: archetype not yet available → fall back
        if not resolved.is_available:
            general = ARCHETYPE_REGISTRY.get(AgentArchetypeId.GENERAL_ASSISTANT)
            logger.info(
                "archetype_not_available",
                requested=resolved.archetype_id.value,
                fallback=general.archetype_id.value,
            )
            return ArchetypeSelection(
                archetype=general,
                intent=intent,
                fell_back=True,
                fallback_reason=f"archetype_unavailable:{resolved.archetype_id.value}",
            )

        # Rule 2: low confidence on a specialist → fall back
        is_general = resolved.archetype_id == AgentArchetypeId.GENERAL_ASSISTANT
        if not is_general and intent.confidence < _SPECIALIST_CONFIDENCE_THRESHOLD:
            general = ARCHETYPE_REGISTRY.get(AgentArchetypeId.GENERAL_ASSISTANT)
            logger.info(
                "archetype_low_confidence_fallback",
                intent=intent.label.value,
                confidence=intent.confidence,
                threshold=_SPECIALIST_CONFIDENCE_THRESHOLD,
            )
            return ArchetypeSelection(
                archetype=general,
                intent=intent,
                fell_back=True,
                fallback_reason=(
                    f"low_confidence:{intent.confidence:.2f}<{_SPECIALIST_CONFIDENCE_THRESHOLD}"
                ),
            )

        logger.debug(
            "archetype_selected",
            archetype=resolved.archetype_id.value,
            intent=intent.label.value,
            confidence=intent.confidence,
        )
        return ArchetypeSelection(archetype=resolved, intent=intent)

    def dispatch_label(self, label: IntentLabel, confidence: float = 1.0) -> ArchetypeSelection:
        """Convenience: dispatch by label + confidence without a full IntentResult."""
        intent = IntentResult(label=label, confidence=confidence, method="direct")
        return self.dispatch(intent)


# Module-level singleton
intent_dispatcher = IntentDispatcher()

__all__ = [
    "ArchetypeSelection",
    "IntentDispatcher",
    "intent_dispatcher",
]
