"""Provider instance lifecycle: creation, circuit state, and preflight."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional


def startup_preflight(dispatcher: Any, logger: Any) -> None:
    """Log configured vs. unconfigured providers and kick off background tasks."""
    configured = []
    unconfigured = []
    for pid in dispatcher._configs:
        if pid == "mock":
            continue
        if dispatcher.is_configured(pid):
            configured.append(pid)
        else:
            unconfigured.append(pid)
    logger.info(
        "provider_preflight",
        configured=configured,
        configured_count=len(configured),
        unconfigured=unconfigured,
        unconfigured_count=len(unconfigured),
        total=len(configured) + len(unconfigured),
    )
    if not configured:
        logger.warning(
            "no_providers_configured",
            hint="Set API key env vars for at least one provider",
        )
    dispatcher.start_background_tasks()


def ensure_provider(
    dispatcher: Any,
    provider_id: str,
    canonical_fn: Callable[[Optional[str]], Optional[str]],
    logger: Any,
) -> Optional[Any]:
    """Instantiate and cache a provider; return None if unavailable."""
    canonical_id = canonical_fn(provider_id) or provider_id
    provider = dispatcher._providers.get(canonical_id)
    if provider is not None:
        return provider

    if canonical_id not in dispatcher._class_map:
        logger.warning("no_class_for_provider", provider=canonical_id)
        return None

    source_config = dict(dispatcher._configs.get(canonical_id, {}))
    try:
        provider = dispatcher._registry.create_from_source(canonical_id, source_config)
    except Exception as exc:
        logger.warning(
            "provider_init_failed",
            provider=canonical_id,
            error=dispatcher._sanitize_error(exc),
        )
        return None
    dispatcher._providers[canonical_id] = provider
    if canonical_id in dispatcher._pending_circuit_restores:
        apply_circuit_state(provider, dispatcher._pending_circuit_restores[canonical_id])
    return provider


def apply_circuit_state(provider: Any, state: Dict[str, Any]) -> None:
    """Restore a previously-persisted circuit breaker state onto a provider."""
    from ..base import ProviderCircuitState  # noqa: PLC0415

    circuit_state = state.get("circuit_state") or "closed"
    failure_count = int(state.get("failure_count") or 0)
    transient = int(state.get("transient_failure_count") or 0)
    open_until = float(state.get("circuit_open_until") or 0.0)

    if circuit_state == ProviderCircuitState.HARD_OPEN:
        provider._circuit_state = ProviderCircuitState.HARD_OPEN
        provider._circuit_open_until = float("inf")
        provider._failure_count = failure_count
        provider._transient_failure_count = transient
    elif circuit_state == ProviderCircuitState.SOFT_OPEN and time.time() < open_until:
        provider._circuit_state = ProviderCircuitState.SOFT_OPEN
        provider._circuit_open_until = open_until
        provider._failure_count = failure_count
        provider._transient_failure_count = transient


def restore_circuit_states(
    dispatcher: Any,
    states: Dict[str, Dict[str, Any]],
) -> None:
    """Bulk-apply circuit states; cache remaining for providers not yet created."""
    dispatcher._pending_circuit_restores = dict(states)
    for provider_id, state in states.items():
        provider = dispatcher._providers.get(provider_id)
        if provider is not None:
            apply_circuit_state(provider, state)
