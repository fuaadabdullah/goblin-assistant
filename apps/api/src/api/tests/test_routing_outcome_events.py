from __future__ import annotations

from api.routing.outcome_events import (
    RoutingOutcomeEvent,
    emit_routing_outcome,
    register_routing_outcome_handler,
)


def test_routing_outcome_events_publish_to_registered_handlers():
    received = []

    def handler(event: RoutingOutcomeEvent) -> None:
        received.append(event)

    register_routing_outcome_handler(handler)

    emit_routing_outcome(provider_id="openai", task_type="chat", success=True)

    assert received[-1] == RoutingOutcomeEvent(
        provider_id="openai",
        task_type="chat",
        success=True,
    )


def test_routing_outcome_events_skip_missing_task_type():
    received = []

    def handler(event: RoutingOutcomeEvent) -> None:
        received.append(event)

    register_routing_outcome_handler(handler)

    emit_routing_outcome(provider_id="openai", task_type=None, success=True)

    assert not received
