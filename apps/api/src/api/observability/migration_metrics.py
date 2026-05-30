"""Operational counters for API compatibility and migration monitoring."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ApiMigrationMetrics:
    _lock: Lock = field(default_factory=Lock)
    request_totals: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    lifecycle_totals: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    lifecycle_status_totals: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    version_usage_totals: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_code_totals: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    provider_probe_totals: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    provider_probe_failures: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_updated_at: str = field(default_factory=_utc_now)

    def _touch(self) -> None:
        self.last_updated_at = _utc_now()

    def record_request(self, *, path: str, lifecycle: str, is_v1: bool, status_code: int) -> None:
        with self._lock:
            self.request_totals["total"] += 1
            self.lifecycle_totals[lifecycle] += 1
            self.lifecycle_status_totals[f"{lifecycle}:{status_code}"] += 1
            self.version_usage_totals["v1" if is_v1 else "legacy_or_other"] += 1
            self.version_usage_totals["legacy"] += int(lifecycle == "legacy" and not is_v1)
            if path.startswith("/api/v1"):
                self.version_usage_totals["v1_prefixed_path"] += 1
            self._touch()

    def record_error_code(self, *, lifecycle: str, error_code: str, status_code: int) -> None:
        with self._lock:
            self.error_code_totals[f"{error_code}:{status_code}"] += 1
            self.error_code_totals[f"lifecycle:{lifecycle}"] += 1
            self._touch()

    def record_provider_probe(
        self,
        *,
        provider_id: str,
        healthy: bool,
        configured: bool,
    ) -> None:
        with self._lock:
            if not configured:
                return
            self.provider_probe_totals[provider_id] += 1
            if not healthy:
                self.provider_probe_failures[provider_id] += 1
            self._touch()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            provider_failure_rate = {}
            for provider_id, total in self.provider_probe_totals.items():
                failures = self.provider_probe_failures.get(provider_id, 0)
                provider_failure_rate[provider_id] = (
                    round(failures / total, 4) if total > 0 else 0.0
                )

            return {
                "updated_at": self.last_updated_at,
                "requests": dict(self.request_totals),
                "lifecycle_totals": dict(self.lifecycle_totals),
                "lifecycle_status_totals": dict(self.lifecycle_status_totals),
                "version_usage_totals": dict(self.version_usage_totals),
                "error_code_totals": dict(self.error_code_totals),
                "provider_probe_totals": dict(self.provider_probe_totals),
                "provider_probe_failures": dict(self.provider_probe_failures),
                "provider_failure_rate": provider_failure_rate,
            }

    def reset_for_tests(self) -> None:
        with self._lock:
            self.request_totals.clear()
            self.lifecycle_totals.clear()
            self.lifecycle_status_totals.clear()
            self.version_usage_totals.clear()
            self.error_code_totals.clear()
            self.provider_probe_totals.clear()
            self.provider_probe_failures.clear()
            self._touch()


migration_metrics = ApiMigrationMetrics()
