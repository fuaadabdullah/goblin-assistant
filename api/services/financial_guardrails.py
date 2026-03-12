"""
Financial guardrails for Goblin Assistant.

Provides rate limiting, timeout handling, and input validation helpers
for financial data fetching and tool execution.
"""

from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter (token-bucket)
# ---------------------------------------------------------------------------

class _TokenBucket:
    """Simple token-bucket rate limiter.

    Args:
        capacity: Max tokens in bucket.
        refill_rate: Tokens added per second.
    """

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self._capacity = capacity
        self._tokens = float(capacity)
        self._refill_rate = refill_rate
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def try_acquire(self) -> bool:
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


# yfinance: ~2000 requests/hour ≈ 0.55 req/s. Use conservative bucket.
_yfinance_bucket = _TokenBucket(capacity=30, refill_rate=0.5)


def check_rate_limit() -> None:
    """Raise if the yfinance rate limit is exhausted."""
    if not _yfinance_bucket.try_acquire():
        raise RateLimitError(
            "Financial data rate limit reached. Please wait a moment and try again."
        )


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class FinancialDataError(Exception):
    """Base class for user-facing financial tool errors."""

    def __init__(self, message: str, ticker: Optional[str] = None) -> None:
        self.ticker = ticker
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"error": str(self)}
        if self.ticker:
            d["ticker"] = self.ticker
        return d


class TickerNotFoundError(FinancialDataError):
    """Raised when a ticker returns no data from the data provider."""


class DataUnavailableError(FinancialDataError):
    """Raised when a specific data point (e.g. FCF, earnings) is unavailable."""


class RateLimitError(FinancialDataError):
    """Raised when the rate limit is exceeded."""


class FetchTimeoutError(FinancialDataError):
    """Raised when a data fetch exceeds the allowed timeout."""


# ---------------------------------------------------------------------------
# Timeout wrapper
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT_S = 15.0

T = TypeVar("T")


async def with_timeout(
    coro,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    ticker: Optional[str] = None,
) -> Any:
    """Run *coro* with a timeout. Raises FetchTimeoutError on expiry."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except asyncio.TimeoutError:
        label = f"{ticker} " if ticker else ""
        raise FetchTimeoutError(
            f"{label}data fetch timed out after {timeout_s:.0f}s. "
            "The market data provider may be slow — please try again.",
            ticker=ticker,
        )


# ---------------------------------------------------------------------------
# Skill-level error wrapper
# ---------------------------------------------------------------------------

def safe_skill(fn: Callable) -> Callable:
    """Decorator that wraps a skill handler so FinancialDataError subclasses
    are returned as structured ``{error: ...}`` dicts instead of propagating
    as exceptions (which would produce ugly 500-style messages)."""

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        try:
            return await fn(*args, **kwargs)
        except FinancialDataError as exc:
            logger.warning(
                "skill_financial_error",
                skill=fn.__name__,
                error=str(exc),
                ticker=exc.ticker,
            )
            return exc.to_dict()
        except ValueError as exc:
            # Ticker validation errors from _validate_ticker
            logger.warning("skill_validation_error", skill=fn.__name__, error=str(exc))
            return {"error": str(exc)}

    return wrapper
