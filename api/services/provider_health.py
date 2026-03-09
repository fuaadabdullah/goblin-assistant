"""
Compatibility health-monitor facade backed by the authoritative dispatcher.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from api.providers.dispatcher import canonical_provider_id, dispatcher
from api.routing.router import registry


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    provider_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    consecutive_failures: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))
    configured: bool = False

    def record_success(self, latency_ms: float) -> None:
        self.latency_samples.append(latency_ms)
        self.last_check = datetime.now(timezone.utc)
        self.last_success = self.last_check
        self.last_error = None
        self.consecutive_failures = 0
        if self.latency_samples:
            self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
        self.status = HealthStatus.HEALTHY

    def record_failure(self, error: str) -> None:
        self.last_check = datetime.now(timezone.utc)
        self.last_error = error
        self.consecutive_failures += 1
        self.status = (
            HealthStatus.UNHEALTHY
            if self.consecutive_failures >= 3
            else HealthStatus.DEGRADED
        )
        if self.latency_samples:
            self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)


class ProviderHealthMonitor:
    def __init__(self, check_interval: int = 30) -> None:
        self.check_interval = check_interval
        self.health_data: Dict[str, ProviderHealth] = {}
        self._running = False
        self._task: Optional[asyncio.Task[Any]] = None

    async def refresh(self, include_hidden: bool = True) -> Dict[str, ProviderHealth]:
        inventory = await dispatcher.get_provider_inventory(include_hidden=include_hidden)
        now = datetime.now(timezone.utc)
        seen: set[str] = set()
        for item in inventory:
            provider_id = item["id"]
            seen.add(provider_id)
            state = self.health_data.get(provider_id) or ProviderHealth(provider_id=provider_id)
            stats = registry.get(provider_id)
            state.success_rate = stats.success_rate
            state.configured = bool(item.get("configured"))
            state.last_check = now
            latency_ms = float(item.get("latency_ms", 0.0) or 0.0)
            if latency_ms > 0:
                state.latency_samples.append(latency_ms)
                state.avg_latency_ms = sum(state.latency_samples) / len(state.latency_samples)

            if not item.get("configured"):
                state.status = HealthStatus.UNKNOWN
                state.last_error = item.get("health_reason") or "Provider not configured"
                state.consecutive_failures = 0
            elif item.get("healthy"):
                state.status = HealthStatus.HEALTHY
                state.last_success = now
                state.last_error = None
                state.consecutive_failures = 0
            else:
                state.status = HealthStatus.UNHEALTHY
                state.last_error = item.get("health_reason") or "Health check failed"
                state.consecutive_failures = max(state.consecutive_failures + 1, 1)

            self.health_data[provider_id] = state

        for provider_id in list(self.health_data.keys()):
            if provider_id not in seen and not include_hidden:
                self.health_data.pop(provider_id, None)

        return self.health_data

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self.refresh(include_hidden=True)
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self.refresh(include_hidden=True)
            except Exception:
                pass
            await asyncio.sleep(self.check_interval)

    async def validate_configured_credentials(self) -> Dict[str, List[str]]:
        inventory = await dispatcher.get_provider_inventory(include_hidden=True)
        configured = [item["id"] for item in inventory if item.get("configured")]
        selectable = [item["id"] for item in inventory if item.get("is_selectable")]
        unconfigured = [item["id"] for item in inventory if not item.get("configured")]
        return {
            "configured": configured,
            "selectable": selectable,
            "unconfigured": unconfigured,
        }

    async def _check_provider(
        self,
        provider_id: str,
        *_args: Any,
        **_kwargs: Any,
    ) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        current = await dispatcher.check_provider(canonical_id)
        state = self.health_data.get(canonical_id) or ProviderHealth(provider_id=canonical_id)
        state.configured = bool(current.get("configured"))
        state.last_check = datetime.now(timezone.utc)
        state.last_error = current.get("health_reason")
        latency_ms = float(current.get("latency_ms", 0.0) or 0.0)
        if latency_ms > 0:
            state.latency_samples.append(latency_ms)
            state.avg_latency_ms = sum(state.latency_samples) / len(state.latency_samples)
        if not current.get("configured"):
            state.status = HealthStatus.UNKNOWN
        elif current.get("healthy"):
            state.status = HealthStatus.HEALTHY
            state.last_success = state.last_check
            state.consecutive_failures = 0
        else:
            state.status = HealthStatus.UNHEALTHY
            state.consecutive_failures = max(state.consecutive_failures + 1, 1)
        stats = registry.get(canonical_id)
        state.success_rate = stats.success_rate
        self.health_data[canonical_id] = state
        return self.get_status(canonical_id)

    async def probe_provider(self, provider_id: str) -> Dict[str, Any]:
        return await self._check_provider(provider_id)

    def is_available(self, provider_id: str) -> bool:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is None:
            try:
                provider = dispatcher.get_provider(canonical_id)
            except KeyError:
                return False
            return dispatcher.is_configured(canonical_id) and provider.is_available()
        return state.configured and state.status in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}

    def get_status(self, provider_id: str) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is None:
            if dispatcher.get_provider_config(canonical_id):
                return {
                    "provider_id": canonical_id,
                    "status": HealthStatus.UNKNOWN.value,
                    "configured": dispatcher.is_configured(canonical_id),
                    "last_check": None,
                    "last_success": None,
                    "last_error": None,
                    "avg_latency_ms": 0.0,
                    "success_rate": 1.0,
                    "consecutive_failures": 0,
                }
            return {"error": f"Unknown provider: {provider_id}"}

        return {
            "provider_id": canonical_id,
            "status": state.status.value,
            "configured": state.configured,
            "last_check": state.last_check.isoformat() if state.last_check else None,
            "last_success": state.last_success.isoformat() if state.last_success else None,
            "last_error": state.last_error,
            "avg_latency_ms": round(state.avg_latency_ms, 1),
            "success_rate": round(state.success_rate, 3),
            "consecutive_failures": state.consecutive_failures,
        }

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        return {
            provider_id: self.get_status(provider_id)
            for provider_id in sorted(self.health_data.keys())
        }

    def get_healthy_providers(self) -> List[str]:
        return [
            provider_id
            for provider_id, state in self.health_data.items()
            if state.status == HealthStatus.HEALTHY and state.configured
        ]

    def get_available_providers(self) -> List[str]:
        return [
            provider_id
            for provider_id, state in self.health_data.items()
            if state.configured and state.status in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}
        ]

    def get_latency(self, provider_id: str) -> float:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is not None and state.avg_latency_ms > 0:
            return state.avg_latency_ms
        return registry.get(canonical_id).ewma_latency_ms

    def get_best_providers(self, limit: int = 5) -> List[str]:
        candidates = self.get_available_providers()
        candidates.sort(
            key=lambda provider_id: (
                self.get_latency(provider_id),
                -self.health_data[provider_id].success_rate,
            )
        )
        return candidates[:limit]


health_monitor = ProviderHealthMonitor()


def get_health_monitor() -> ProviderHealthMonitor:
    return health_monitor
