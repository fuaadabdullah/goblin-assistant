"""Provider-health boundary for routing feature extraction."""

from __future__ import annotations

import importlib
from typing import Any, Mapping, Protocol, Sequence


class HealthProvider(Protocol):
    """Supplies provider availability snapshots to routing code."""

    def availability_for(self, provider_ids: Sequence[str]) -> Mapping[str, bool]:
        """Return cached availability for the requested provider ids."""


class StaticHealthProvider:
    """Deterministic health provider for tests and degraded local operation."""

    def __init__(self, availability: Mapping[str, bool] | None = None) -> None:
        self._availability = dict(availability or {})

    def availability_for(self, provider_ids: Sequence[str]) -> Mapping[str, bool]:
        return {
            provider_id: self._availability.get(provider_id, True) for provider_id in provider_ids
        }


class CachedProviderHealthProvider:
    """Reads cached provider-health state without probing or executing providers."""

    _AVAILABLE_STATUSES = {"healthy", "degraded"}

    def availability_for(self, provider_ids: Sequence[str]) -> Mapping[str, bool]:
        requested = list(provider_ids)
        availability = {provider_id: True for provider_id in requested}
        if not requested:
            return availability

        try:
            health_monitor = importlib.import_module("api.services.provider_health").health_monitor
            status_by_provider = health_monitor.get_all_status(include_hidden=False)
        except Exception:
            return availability

        if not isinstance(status_by_provider, Mapping):
            return availability

        for provider_id in requested:
            status = status_by_provider.get(provider_id)
            if not isinstance(status, Mapping):
                continue
            availability[provider_id] = _status_is_available(status)

        return availability


def _status_is_available(status: Mapping[str, Any]) -> bool:
    if status.get("error"):
        return False
    return bool(status.get("configured")) and status.get("status") in {
        "healthy",
        "degraded",
    }


health_provider = CachedProviderHealthProvider()
