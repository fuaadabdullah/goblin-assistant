"""Shared outbound HTTP client with bounded retries and short-lived caching."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()


def _cache_key(url: str, params: Mapping[str, Any] | None) -> str:
    """Build a deterministic key without putting authentication headers in it."""
    return f"{url}?{sorted((params or {}).items())}"


async def get_http_client(*, timeout: float = 15.0) -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        async with _client_lock:
            if _client is None or _client.is_closed:
                _client = httpx.AsyncClient(timeout=timeout)
    return _client


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {
        429,
        500,
        502,
        503,
        504,
    }


@retry(
    retry=retry_if_exception(_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.2, max=2.0),
    reraise=True,
)
async def _get(
    url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
) -> httpx.Response:
    client = await get_http_client()
    response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response


async def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    ttl: float = 20.0,
) -> Any:
    cache_key = _cache_key(url, params)
    async with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]

    response = await _get(url, params=params, headers=headers)
    value = response.json()
    async with _cache_lock:
        _cache[cache_key] = (time.monotonic() + ttl, value)
    return value


async def get_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    ttl: float = 20.0,
) -> str:
    """Fetch a text response using the same bounded retry policy as JSON GETs."""
    cache_key = _cache_key(url, params)
    async with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]

    value = (await _get(url, params=params, headers=headers)).text
    async with _cache_lock:
        _cache[cache_key] = (time.monotonic() + ttl, value)
    return value


async def close_http_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
    async with _cache_lock:
        _cache.clear()
