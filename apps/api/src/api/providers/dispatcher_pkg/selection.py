"""Provider selection helpers used by the compatibility dispatcher facade."""

from __future__ import annotations

from typing import Any, Optional


async def select_provider(providers: list, *, preferred: Optional[str] = None) -> Any:
    """Select the best provider from a list based on health and latency."""
    if preferred:
        for provider in providers:
            health = await provider.health_check()
            if provider.provider_id == preferred and health.healthy:
                return provider

    healthy = []
    for provider in providers:
        health = await provider.health_check()
        if health.healthy:
            healthy.append((health.latency_ms, provider))

    if healthy:
        healthy.sort(key=lambda item: item[0])
        return healthy[0][1]

    all_checked = []
    for provider in providers:
        health = await provider.health_check()
        all_checked.append((health.latency_ms, provider))
    all_checked.sort(key=lambda item: item[0])
    return all_checked[0][1] if all_checked else providers[0]


async def invoke_with_fallback(prompt: str, *, providers: list) -> Any:
    """Try each provider in order; raise if all fail."""
    last_exc: Optional[Exception] = None
    for provider in providers:
        try:
            return await provider.invoke(prompt)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise last_exc or RuntimeError("No providers available")
