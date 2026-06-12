"""Abstract base class for quota storage backends (Redis, in-memory)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .models import QuotaReservation


class QuotaBackend(ABC):
    """Unified storage interface; callers never pick Redis vs memory directly."""

    @property
    @abstractmethod
    def last_skip_reason(self) -> str:
        """Reason the last reserve() returned False, or '' on success."""

    def reset(self) -> None:
        """Clear all state. Called between pytest test cases."""

    @abstractmethod
    async def reserve(
        self,
        reservation: QuotaReservation,
        provider_limit: Any,
        shared_limit: Any,
    ) -> bool:
        """Atomically check capacity and record the reservation."""

    @abstractmethod
    async def commit(
        self,
        reservation: QuotaReservation,
        *,
        actual_input_tokens: int = 0,
        actual_output_tokens: int = 0,
    ) -> None:
        """Convert a reservation to a committed usage record."""

    @abstractmethod
    async def release(self, reservation: QuotaReservation) -> None:
        """Cancel a reservation without committing (error / cancellation)."""

    @abstractmethod
    async def mark_rate_limited(
        self,
        scopes: List[str],
        cooldown_seconds: int,
    ) -> None:
        """Set a cooldown on the given scopes after receiving a rate-limit error."""

    @abstractmethod
    async def can_attempt(self, provider_scope: str, model_scope: str) -> bool:
        """Return False if either scope is currently in cooldown."""

    @abstractmethod
    async def scope_snapshot(
        self,
        scope: str,
        limit: Any,
        wkey: str,
    ) -> Dict[str, Any]:
        """Return current usage counters and limit info for a scope."""
