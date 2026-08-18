"""Service-level adapter for intent archetype dispatch.

This isolates direct imports of the agents dispatcher behind the services
boundary so chat routes/stages do not couple to agents modules.
"""

from __future__ import annotations

from typing import Any


def dispatch_intent_archetype(intent: Any) -> Any:
    """Dispatch an intent result to an archetype selection.

    The underlying dispatcher may raise; callers decide whether to degrade
    gracefully or fail closed.
    """
    from api.agents.dispatcher import intent_dispatcher

    return intent_dispatcher.dispatch(intent)


__all__ = ["dispatch_intent_archetype"]
