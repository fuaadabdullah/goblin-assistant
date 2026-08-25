"""
Canonical provider-health subsystem for routing and health reporting.

This service owns the rolling availability state used by routing decisions.
It seeds provider state from configuration, probes providers asynchronously
after boot, and folds in passive request observations so routing can rely on
evidence instead of config presence.
"""

from __future__ import annotations

import asyncio
import importlib
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

from api.core.contracts import ProviderHealthUpdatedPayload
from api.observability.events import event_emitter
from api.observability.migration_metrics import migration_metrics
from api.ops.integrations.jira import publish_provider_health_incident
from api.providers.domain import ProviderHealthSnapshot, ProviderHealthStatus
from api.providers.supabase_events import upsert_provider_status
from api.routing.router import registry


class _DispatcherProxy:
    def get_provider_inventory(self, *args: Any, **kwargs: Any) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return module.dispatcher.get_provider_inventory(*args, **kwargs)

    def get_provider(self, *args: Any, **kwargs: Any) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return module.dispatcher.get_provider(*args, **kwargs)

    def get_provider_config(self, *args: Any, **kwargs: Any) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return module.dispatcher.get_provider_config(*args, **kwargs)

    def is_configured(self, *args: Any, **kwargs: Any) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return module.dispatcher.is_configured(*args, **kwargs)

    def check_provider(self, *args: Any, **kwargs: Any) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return module.dispatcher.check_provider(*args, **kwargs)

    def provider_ids(self, *args: Any, **kwargs: Any) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return module.dispatcher.provider_ids(*args, **kwargs)

    def list_providers(self, *args: Any, **kwargs: Any) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return module.dispatcher.list_providers(*args, **kwargs)

    def health_all(self, *args: Any, **kwargs: Any) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return module.dispatcher.health_all(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        module = importlib.import_module("api.providers.dispatcher")
        return getattr(module, name)


dispatcher = _DispatcherProxy()


def _dispatcher() -> _DispatcherProxy:
    return dispatcher


def canonical_provider_id(provider_id: str) -> Optional[str]:
    module = importlib.import_module("api.providers.dispatcher")
    return module.canonical_provider_id(provider_id)


def _average_latency(samples: Deque[float]) -> float:
    if not samples:
        return 0.0
    return sum(samples) / len(samples)


def _percentile_latency(samples: Deque[float], percentile: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(float(sample) for sample in samples)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _latency_percentiles(samples: Deque[float]) -> Dict[str, float]:
    return {
        "p50": round(_percentile_latency(samples, 0.50), 1),
        "p90": round(_percentile_latency(samples, 0.90), 1),
        "p95": round(_percentile_latency(samples, 0.95), 1),
        "p99": round(_percentile_latency(samples, 0.99), 1),
    }


def _push_status(provider_id: str, state: "ProviderHealthState") -> None:
    """Fire-and-forget persistence of the latest provider-health snapshot."""

    try:
        disp = importlib.import_module("api.providers.dispatcher").dispatcher
        provider = disp._providers.get(provider_id)
        circuit_status: Dict[str, Any] = {}
        if provider is not None:
            circuit_status_fn = getattr(provider, "circuit_status", None)
            if callable(circuit_status_fn):
                try:
                    circuit_status = dict(circuit_status_fn())
                except Exception:
                    circuit_status = {}
        if circuit_status:
            circuit_state = str(
                circuit_status.get("state")
                or circuit_status.get("circuit_state")
                or getattr(provider, "circuit_state", state.circuit_state)
            )
            failure_count = int(
                circuit_status.get("failure_count", state.consecutive_failures) or 0
            )
            transient_failure_count = int(
                circuit_status.get(
                    "transient_failure_count",
                    getattr(provider, "_transient_failure_count", 0) if provider else 0,
                )
                or 0
            )
            circuit_open_until = circuit_status.get("open_until")
        else:
            circuit_state = str(
                getattr(provider, "circuit_state", state.circuit_state)
                if provider is not None
                else state.circuit_state
            )
            failure_count = int(state.consecutive_failures)
            transient_failure_count = int(
                getattr(provider, "_transient_failure_count", 0) if provider else 0
            )
            circuit_open_until = (
                getattr(provider, "_circuit_open_until", None) if provider else None
            )

        upsert_provider_status(
            provider_id,
            is_healthy=state.status == HealthStatus.HEALTHY,
            circuit_state=circuit_state,
            failure_count=failure_count,
            transient_failure_count=transient_failure_count,
            circuit_open_until=circuit_open_until,
            avg_latency_ms=(state.avg_latency_ms if state.avg_latency_ms > 0 else None),
            error_message=state.last_error,
        )
    except Exception:
        return


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "unhealthy"
    UNKNOWN = "unknown"
    BILLING = "billing_issue"


_TO_DOMAIN_STATUS = {
    HealthStatus.HEALTHY: ProviderHealthStatus.HEALTHY,
    HealthStatus.DEGRADED: ProviderHealthStatus.DEGRADED,
    HealthStatus.UNHEALTHY: ProviderHealthStatus.UNHEALTHY,
    HealthStatus.UNKNOWN: ProviderHealthStatus.UNKNOWN,
    HealthStatus.BILLING: ProviderHealthStatus.BILLING_ISSUE,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _failure_category_from_reason(reason: Optional[str]) -> Optional[str]:
    if not reason:
        return None
    normalized = reason.strip().lower()
    if any(token in normalized for token in ("quota", "billing", "payment", "insufficient")):
        return "billing"
    if any(token in normalized for token in ("timeout", "timed out", "deadline exceeded")):
        return "timeout"
    if any(
        token in normalized
        for token in ("unauthorized", "forbidden", "invalid api key", "401", "403")
    ):
        return "auth"
    if any(token in normalized for token in ("unreachable", "connection", "dns", "refused")):
        return "connection"
    return "unknown"


@dataclass
class ProviderHealthState:
    """Rolling health state for one provider."""

    provider_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    availability_state: str = "unknown"
    last_check: Optional[datetime] = None
    last_probe_at: Optional[datetime] = None
    last_observation_at: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_error: Optional[str] = None
    last_failure_reason: Optional[str] = None
    last_failure_category: Optional[str] = None
    avg_latency_ms: float = 0.0
    latency_ewma_ms: float = 0.0
    failure_rate_ewma: float = 0.0
    success_rate: float = 1.0
    consecutive_failures: int = 0
    latency_samples: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    configured: bool = False
    circuit_state: str = "closed"
    circuit_open_until: Optional[datetime] = None
    probe_count: int = 0
    observation_count: int = 0
    last_observed_latency_ms: float = 0.0
    first_seen_at: datetime = field(default_factory=_now)

    def _update_latency(self, latency_ms: float) -> None:
        if latency_ms <= 0:
            return
        self.latency_samples.append(float(latency_ms))
        self.avg_latency_ms = _average_latency(self.latency_samples)
        if self.latency_ewma_ms <= 0:
            self.latency_ewma_ms = float(latency_ms)
        else:
            self.latency_ewma_ms = 0.2 * float(latency_ms) + 0.8 * self.latency_ewma_ms

    def _update_failure_rate(self, failure: bool) -> None:
        sample = 1.0 if failure else 0.0
        if self.failure_rate_ewma <= 0:
            self.failure_rate_ewma = sample
        else:
            self.failure_rate_ewma = 0.2 * sample + 0.8 * self.failure_rate_ewma
        self.success_rate = max(0.0, min(1.0, 1.0 - self.failure_rate_ewma))

    def _refresh_availability(self, now: datetime) -> None:
        if not self.configured:
            self.status = HealthStatus.UNKNOWN
            self.availability_state = "unknown"
            self.circuit_state = "closed"
            self.circuit_open_until = None
            return

        if self.circuit_open_until is not None and self.circuit_open_until > now:
            self.status = HealthStatus.DOWN
            self.availability_state = "down"
            return

        if self.last_check is None and self.last_observation_at is None:
            self.status = HealthStatus.UNKNOWN
            self.availability_state = "unknown"
            return

        if self.last_failure_category == "billing":
            self.status = HealthStatus.BILLING
            self.availability_state = "billing_issue"
            return

        degraded_latency = self.latency_ewma_ms >= 1200.0 if self.latency_ewma_ms > 0 else False
        degraded_failure_rate = self.failure_rate_ewma >= 0.18
        down_failure_rate = self.failure_rate_ewma >= 0.6

        if self.consecutive_failures >= 4 or down_failure_rate:
            self.status = HealthStatus.DOWN
            self.availability_state = "down"
            self.circuit_state = "hard_open"
            if self.circuit_open_until is None or self.circuit_open_until <= now:
                self.circuit_open_until = now + timedelta(seconds=180)
            return

        if self.consecutive_failures >= 2 or degraded_latency or degraded_failure_rate:
            self.status = HealthStatus.DEGRADED
            self.availability_state = "degraded"
            if self.circuit_state == "closed":
                self.circuit_state = "soft_open"
            if self.circuit_open_until is None or self.circuit_open_until <= now:
                self.circuit_open_until = now + timedelta(seconds=60)
            return

        self.status = HealthStatus.HEALTHY
        self.availability_state = "healthy"
        self.circuit_state = "closed"
        self.circuit_open_until = None

    def mark_configured(self, configured: bool) -> None:
        self.configured = configured
        if not configured:
            self.status = HealthStatus.UNKNOWN
            self.availability_state = "unknown"
            self.circuit_state = "closed"
            self.circuit_open_until = None

    def record_success(self, latency_ms: float, *, source: str = "probe") -> None:
        now = _now()
        self.last_check = now
        if source == "probe":
            self.last_probe_at = now
            self.probe_count += 1
        else:
            self.last_observation_at = now
            self.observation_count += 1
        self.last_success = now
        self.last_failure = None
        self.last_error = None
        self.last_failure_reason = None
        self.last_failure_category = None
        self.consecutive_failures = 0
        self.last_observed_latency_ms = float(latency_ms or 0.0)
        self._update_latency(latency_ms)
        self._update_failure_rate(failure=False)
        self._refresh_availability(now)

    def record_failure(
        self,
        error: str,
        *,
        latency_ms: float = 0.0,
        source: str = "probe",
        billing_issue: bool = False,
        error_category: Optional[str] = None,
    ) -> None:
        now = _now()
        self.last_check = now
        if source == "probe":
            self.last_probe_at = now
            self.probe_count += 1
        else:
            self.last_observation_at = now
            self.observation_count += 1
        self.last_failure = now
        self.last_error = error
        self.last_failure_reason = error
        self.last_failure_category = error_category or _failure_category_from_reason(error)
        self.consecutive_failures += 1
        self.last_observed_latency_ms = float(latency_ms or 0.0)
        self._update_latency(latency_ms)
        self._update_failure_rate(failure=True)
        if billing_issue:
            self.status = HealthStatus.BILLING
            self.availability_state = "billing_issue"
            self.circuit_state = "closed"
            self.circuit_open_until = None
            return
        self._refresh_availability(now)

    def record_observation(
        self,
        *,
        ok: bool,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
        billing_issue: bool = False,
        error_category: Optional[str] = None,
    ) -> None:
        if ok:
            self.record_success(latency_ms, source="observation")
        else:
            self.record_failure(
                error or "provider request failed",
                latency_ms=latency_ms,
                source="observation",
                billing_issue=billing_issue,
                error_category=error_category,
            )

    @property
    def latency_percentiles_ms(self) -> Dict[str, float]:
        return _latency_percentiles(self.latency_samples)

    def to_snapshot(self) -> ProviderHealthSnapshot:
        checked_at = (
            self.last_check.timestamp() if self.last_check else self.first_seen_at.timestamp()
        )
        return ProviderHealthSnapshot(
            provider_id=self.provider_id,
            healthy=self.status == HealthStatus.HEALTHY,
            status=_TO_DOMAIN_STATUS.get(self.status, ProviderHealthStatus.UNKNOWN),
            latency_ms=self.latency_ewma_ms if self.latency_ewma_ms > 0 else self.avg_latency_ms,
            error=self.last_error,
            billing_issue=self.status == HealthStatus.BILLING,
            checked_at=checked_at,
        )


ProviderHealth = ProviderHealthState


class ProviderHealthService:
    def __init__(
        self,
        check_interval: float = 180.0,
        *,
        probe_timeout_seconds: float = 12.0,
        startup_jitter_seconds: float = 3.0,
        periodic_jitter_seconds: float = 30.0,
    ) -> None:
        self.check_interval = float(check_interval)
        self.probe_timeout_seconds = float(probe_timeout_seconds)
        self.startup_jitter_seconds = float(startup_jitter_seconds)
        self.periodic_jitter_seconds = float(periodic_jitter_seconds)
        self.health_data: Dict[str, ProviderHealth] = {}
        self._running = False
        self._task: Optional[asyncio.Task[Any]] = None
        self._lock = asyncio.Lock()

    def _is_stale(self, state: Optional[ProviderHealth]) -> bool:
        if state is None:
            return True
        latest = max(
            (
                item
                for item in (
                    state.last_check,
                    state.last_probe_at,
                    state.last_observation_at,
                    state.last_success,
                    state.last_failure,
                )
                if item is not None
            ),
            default=None,
        )
        if latest is None:
            return True
        age = _now() - latest
        return age.total_seconds() > self.check_interval * 2

    def _provider_ids(self, include_hidden: bool = False) -> List[str]:
        try:
            return list(_dispatcher().provider_ids(include_hidden=include_hidden))
        except Exception:
            return sorted(self.health_data.keys())

    def _sync_configured_providers(self, include_hidden: bool = True) -> None:
        try:
            inventory = list(_dispatcher().list_providers(include_hidden=include_hidden))
        except Exception:
            return

        seen: set[str] = set()
        for item in inventory:
            provider_id = str(item.get("id") or "").strip()
            if not provider_id:
                continue
            seen.add(provider_id)
            state = self.health_data.get(provider_id)
            if state is None:
                state = ProviderHealth(provider_id=provider_id)
                self.health_data[provider_id] = state
            state.mark_configured(bool(item.get("configured")))

        for provider_id in list(self.health_data.keys()):
            if provider_id not in seen:
                state = self.health_data[provider_id]
                if not include_hidden and not state.configured:
                    self.health_data.pop(provider_id, None)

    async def _emit_health_event(self, provider_id: str, state: ProviderHealth) -> None:
        try:
            occurred_at = (state.last_check or _now()).isoformat()
            payload = ProviderHealthUpdatedPayload(
                provider_id=provider_id,
                status=state.status.value,
                configured=state.configured,
                healthy=state.status == HealthStatus.HEALTHY,
                cache_stale=self._is_stale(state),
                avg_latency_ms=round(state.avg_latency_ms, 1),
                success_rate=round(state.success_rate, 3),
                consecutive_failures=state.consecutive_failures,
                last_error=state.last_error,
            )
            await event_emitter.emit(
                "provider.health.updated",
                source="api.services.provider_health",
                payload=payload,
            )
            await publish_provider_health_incident(payload, occurred_at=occurred_at)
        except Exception:
            return

    def _state_for(self, provider_id: str) -> ProviderHealth:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is None:
            state = ProviderHealth(provider_id=canonical_id)
            self.health_data[canonical_id] = state
        try:
            state.mark_configured(bool(_dispatcher().is_configured(canonical_id)))
        except Exception:
            pass
        return state

    async def _probe_provider(
        self,
        provider_id: str,
        *,
        deep_probe: bool = False,
    ) -> ProviderHealth:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self._state_for(canonical_id)
        previous_status = state.status
        try:
            current = await asyncio.wait_for(
                _dispatcher().check_provider(canonical_id),
                timeout=max(0.5, self.probe_timeout_seconds),
            )
        except asyncio.TimeoutError:
            state.record_failure(
                f"timed out after {int(self.probe_timeout_seconds)}s",
                latency_ms=float(self.probe_timeout_seconds * 1000.0),
                source="probe",
                error_category="timeout",
            )
            migration_metrics.record_provider_probe(
                provider_id=canonical_id,
                healthy=False,
                configured=state.configured,
            )
            _push_status(canonical_id, state)
            await self._emit_health_event(canonical_id, state)
            return state
        except Exception as exc:
            state.record_failure(
                str(exc),
                source="probe",
                error_category="unknown",
            )
            migration_metrics.record_provider_probe(
                provider_id=canonical_id,
                healthy=False,
                configured=state.configured,
            )
            _push_status(canonical_id, state)
            await self._emit_health_event(canonical_id, state)
            return state

        state.mark_configured(bool(current.get("configured")))
        latency_ms = float(current.get("latency_ms", 0.0) or 0.0)
        billing_issue = bool(current.get("billing_issue"))
        healthy = bool(current.get("healthy"))
        health_reason = str(current.get("health_reason") or "").strip()

        if state.configured:
            if healthy:
                state.record_success(latency_ms, source="probe")
            else:
                state.record_failure(
                    health_reason
                    or ("billing/quota issue" if billing_issue else "health check failed"),
                    latency_ms=latency_ms,
                    source="probe",
                    billing_issue=billing_issue,
                    error_category="billing" if billing_issue else None,
                )
        else:
            state.last_check = _now()
            state.last_probe_at = state.last_check
            state.last_error = health_reason or "Provider not configured"
            state.last_failure_reason = state.last_error
            state.last_failure_category = None
            state.status = HealthStatus.UNKNOWN
            state.availability_state = "unknown"
            state.consecutive_failures = 0
            state._update_latency(latency_ms)
            state._update_failure_rate(failure=False)

        if deep_probe and state.status in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}:
            try:
                provider = _dispatcher().get_provider(canonical_id)
                probe = await asyncio.wait_for(
                    provider.warmup(),
                    timeout=max(0.5, self.probe_timeout_seconds),
                )
                probe_latency = float(getattr(probe, "latency_ms", 0.0) or 0.0)
                if getattr(probe, "ok", False):
                    state.record_success(probe_latency, source="probe")
                else:
                    state.record_failure(
                        getattr(probe, "error", None) or "Warmup failed",
                        latency_ms=probe_latency,
                        source="probe",
                    )
            except Exception as exc:
                state.record_failure(str(exc), source="probe")

        migration_metrics.record_provider_probe(
            provider_id=canonical_id,
            healthy=bool(current.get("healthy")),
            configured=bool(current.get("configured")),
        )
        _push_status(canonical_id, state)
        if previous_status != state.status:
            await self._emit_health_event(canonical_id, state)
        return state

    async def _run_probe_cycle(
        self,
        provider_ids: List[str],
        *,
        deep_probe: bool = False,
        jitter_seconds: float = 0.0,
    ) -> None:
        async def _probe_with_jitter(provider_id: str, offset: float) -> None:
            if offset > 0:
                await asyncio.sleep(offset)
            try:
                await self._probe_provider(provider_id, deep_probe=deep_probe)
            except Exception:
                # Probe failures are already reflected in state; this keeps the loop alive.
                return

        tasks = []
        for provider_id in provider_ids:
            offset = random.uniform(0.0, max(0.0, jitter_seconds)) if jitter_seconds > 0 else 0.0
            tasks.append(asyncio.create_task(_probe_with_jitter(provider_id, offset)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def probe_all(
        self,
        include_hidden: bool = True,
        deep_probe: bool = False,
    ) -> Dict[str, ProviderHealth]:
        self._sync_configured_providers(include_hidden=include_hidden)
        provider_ids = self._provider_ids(include_hidden=include_hidden)
        await self._run_probe_cycle(provider_ids, deep_probe=deep_probe, jitter_seconds=0.0)
        return dict(self.health_data)

    async def refresh(
        self,
        include_hidden: bool = True,
        deep_probe: bool = False,
    ) -> Dict[str, ProviderHealth]:
        return await self.probe_all(include_hidden=include_hidden, deep_probe=deep_probe)

    async def _startup_probe_once(self) -> None:
        await asyncio.sleep(random.uniform(0.0, max(0.0, self.startup_jitter_seconds)))
        while self._running:
            try:
                await self.probe_all(include_hidden=True, deep_probe=False)
                break
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(0.5)

    async def _background_loop(self) -> None:
        try:
            await self._startup_probe_once()
            while self._running:
                jitter = random.uniform(0.0, max(0.0, self.periodic_jitter_seconds))
                await asyncio.sleep(max(0.5, self.check_interval + jitter))
                if not self._running:
                    break
                await self.probe_all(include_hidden=True, deep_probe=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep the service alive even if one loop iteration fails unexpectedly.
            if self._running:
                self._task = asyncio.create_task(self._background_loop())

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._sync_configured_providers(include_hidden=True)
        self._task = asyncio.create_task(self._background_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def validate_configured_credentials(self) -> Dict[str, List[str]]:
        inventory = await _dispatcher().get_provider_inventory(include_hidden=True)
        configured = [item["id"] for item in inventory if item.get("configured")]
        selectable = [item["id"] for item in inventory if item.get("is_selectable")]
        unconfigured = [item["id"] for item in inventory if not item.get("configured")]
        invalid_credentials: List[str] = []
        unreachable: List[str] = []

        for item in inventory:
            provider_id = str(item.get("id") or "")
            if not provider_id or not item.get("configured"):
                continue
            reason = str(item.get("health_reason") or "").lower()
            if item.get("billing_issue") or any(
                token in reason for token in ("quota", "billing", "unauthorized", "invalid api key")
            ):
                invalid_credentials.append(provider_id)
            elif not item.get("healthy"):
                unreachable.append(provider_id)

        return {
            "configured": configured,
            "selectable": selectable,
            "unconfigured": unconfigured,
            "invalid_credentials": invalid_credentials,
            "unreachable": unreachable,
        }

    async def observe_request(
        self,
        provider_id: str,
        *,
        ok: bool,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
        billing_issue: bool = False,
        error_category: Optional[str] = None,
    ) -> ProviderHealth:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self._state_for(canonical_id)
        state.record_observation(
            ok=ok,
            latency_ms=latency_ms,
            error=error,
            billing_issue=billing_issue,
            error_category=error_category,
        )
        migration_metrics.record_provider_probe(
            provider_id=canonical_id,
            healthy=ok,
            configured=state.configured,
        )
        _push_status(canonical_id, state)
        return state

    async def note_request_result(
        self,
        provider_id: str,
        *,
        ok: bool,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
        billing_issue: bool = False,
        error_category: Optional[str] = None,
    ) -> ProviderHealth:
        return await self.observe_request(
            provider_id,
            ok=ok,
            latency_ms=latency_ms,
            error=error,
            billing_issue=billing_issue,
            error_category=error_category,
        )

    async def _check_provider(
        self,
        provider_id: str,
        *_args: Any,
        **_kwargs: Any,
    ) -> Dict[str, Any]:
        snapshot = await self._probe_provider(provider_id, deep_probe=False)
        return self.get_status(snapshot.provider_id)

    async def probe_provider(self, provider_id: str) -> Dict[str, Any]:
        return await self._check_provider(provider_id)

    def is_available(self, provider_id: str) -> bool:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is None:
            return False
        if not state.configured:
            return False
        if state.circuit_open_until is not None and state.circuit_open_until > _now():
            return False
        return state.status in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}

    def success_rate(self, provider_id: str) -> float:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is not None:
            return state.success_rate
        return registry.get(canonical_id).success_rate

    def get_status(self, provider_id: str) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is None:
            if _dispatcher().get_provider_config(canonical_id):
                return {
                    "provider_id": canonical_id,
                    "status": HealthStatus.UNKNOWN.value,
                    "availability_state": "unknown",
                    "configured": _dispatcher().is_configured(canonical_id),
                    "last_check": None,
                    "last_probe_at": None,
                    "last_observation_at": None,
                    "last_success": None,
                    "last_failure": None,
                    "last_error": None,
                    "last_failure_reason": None,
                    "last_failure_category": None,
                    "avg_latency_ms": 0.0,
                    "latency_ewma_ms": 0.0,
                    "latency_percentiles_ms": {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0},
                    "latency_sample_count": 0,
                    "failure_rate_ewma": 0.0,
                    "success_rate": 1.0,
                    "consecutive_failures": 0,
                    "circuit_state": "closed",
                    "circuit_open_until": None,
                    "probe_count": 0,
                    "observation_count": 0,
                    "cache_stale": True,
                    "billing_issue": False,
                }
            return {"error": f"Unknown provider: {provider_id}"}

        return {
            "provider_id": canonical_id,
            "status": state.status.value,
            "availability_state": state.availability_state,
            "configured": state.configured,
            "last_check": _iso(state.last_check),
            "last_probe_at": _iso(state.last_probe_at),
            "last_observation_at": _iso(state.last_observation_at),
            "last_success": _iso(state.last_success),
            "last_failure": _iso(state.last_failure),
            "last_error": state.last_error,
            "last_failure_reason": state.last_failure_reason,
            "last_failure_category": state.last_failure_category,
            "avg_latency_ms": round(state.avg_latency_ms, 1),
            "latency_ewma_ms": round(state.latency_ewma_ms, 1),
            "latency_percentiles_ms": state.latency_percentiles_ms,
            "latency_sample_count": len(state.latency_samples),
            "failure_rate_ewma": round(state.failure_rate_ewma, 3),
            "success_rate": round(state.success_rate, 3),
            "consecutive_failures": state.consecutive_failures,
            "circuit_state": state.circuit_state,
            "circuit_open_until": _iso(state.circuit_open_until),
            "probe_count": state.probe_count,
            "observation_count": state.observation_count,
            "billing_issue": state.status == HealthStatus.BILLING,
            "cache_stale": self._is_stale(state),
        }

    def get_all_status(
        self,
        include_hidden: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        provider_ids = set(self._provider_ids(include_hidden=include_hidden))
        if include_hidden:
            provider_ids.update(self.health_data.keys())
        return {provider_id: self.get_status(provider_id) for provider_id in sorted(provider_ids)}

    def get_status_typed(self, provider_id: str) -> Optional[ProviderHealthSnapshot]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is None:
            if _dispatcher().get_provider_config(canonical_id):
                return ProviderHealthSnapshot(
                    provider_id=canonical_id,
                    healthy=False,
                    status=ProviderHealthStatus.UNKNOWN,
                )
            return None
        return state.to_snapshot()

    def get_all_status_typed(
        self, include_hidden: bool = False
    ) -> Dict[str, ProviderHealthSnapshot]:
        provider_ids = set(self._provider_ids(include_hidden=include_hidden))
        if include_hidden:
            provider_ids.update(self.health_data.keys())
        result: Dict[str, ProviderHealthSnapshot] = {}
        for provider_id in sorted(provider_ids):
            snapshot = self.get_status_typed(provider_id)
            if snapshot is not None:
                result[provider_id] = snapshot
        return result

    def get_healthy_providers(self) -> List[str]:
        return [
            provider_id
            for provider_id, state in self.health_data.items()
            if state.configured and state.status == HealthStatus.HEALTHY
        ]

    def get_available_providers(self) -> List[str]:
        return [
            provider_id
            for provider_id, state in self.health_data.items()
            if state.configured
            and state.status in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}
            and (state.circuit_open_until is None or state.circuit_open_until <= _now())
        ]

    def get_latency(self, provider_id: str) -> float:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        state = self.health_data.get(canonical_id)
        if state is not None:
            if state.latency_ewma_ms > 0:
                return state.latency_ewma_ms
            if state.avg_latency_ms > 0:
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

    def providers_available(self) -> int:
        return len(self.get_available_providers())

    def has_evidence(self) -> bool:
        return any(
            state.last_check is not None or state.last_observation_at is not None
            for state in self.health_data.values()
        )


HealthMonitor = ProviderHealthService


health_monitor = HealthMonitor()


def get_health_monitor() -> ProviderHealthService:
    return health_monitor
