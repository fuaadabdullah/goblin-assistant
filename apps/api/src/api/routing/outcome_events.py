"""Routing outcome event bus.

Registry emits provider outcomes here; learning components subscribe without
the registry knowing which router or model will consume the signal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoutingOutcomeEvent:
    provider_id: str
    task_type: str
    success: bool


RoutingOutcomeHandler = Callable[[RoutingOutcomeEvent], None]

_handlers: List[RoutingOutcomeHandler] = []


def register_routing_outcome_handler(handler: RoutingOutcomeHandler) -> None:
    if handler not in _handlers:
        _handlers.append(handler)


def emit_routing_outcome(
    *,
    provider_id: str,
    task_type: Optional[str],
    success: bool,
) -> None:
    if not task_type:
        return

    event = RoutingOutcomeEvent(
        provider_id=provider_id,
        task_type=task_type,
        success=success,
    )
    for handler in list(_handlers):
        try:
            handler(event)
        except Exception as exc:
            logger.debug("routing_outcome_handler_failed error=%s", exc)
