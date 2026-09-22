"""Shared provider retry policy.

Only transient failures are retried: connection/timeout errors, HTTP 429,
and HTTP 5xx. Authentication, validation, model, and other 4xx failures
fail immediately.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_random_exponential

T = TypeVar("T")


def is_retryable_provider_exception(exc: BaseException) -> bool:
    """Return whether a provider exception is safe to retry automatically."""
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or 500 <= status_code < 600

    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code == 429 or 500 <= status_code < 600

    return isinstance(exc, (httpx.RequestError, ConnectionError, TimeoutError))


async def retry_provider_call(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
) -> T:
    """Run an async provider operation with bounded exponential jitter retries."""
    retrying = AsyncRetrying(
        stop=stop_after_attempt(max(1, attempts)),
        wait=wait_random_exponential(multiplier=0.25, max=4.0),
        retry=retry_if_exception(is_retryable_provider_exception),
        reraise=True,
    )

    async for attempt in retrying:
        with attempt:
            return await operation()

    raise RuntimeError("provider retry loop exited without a result")
