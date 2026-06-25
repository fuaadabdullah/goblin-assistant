"""Provider health checking and inventory."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ..base import ProviderErrorCategory, ProviderHealth, classify_provider_error


def _build_health_result(
    provider_id: str,
    *,
    configured: bool,
    healthy: bool,
    health_state: str,
    health_reason: str,
    is_selectable: bool,
    latency_ms: float,
    circuit_breaker: Optional[Dict[str, Any]] = None,
    warmup: Optional[Dict[str, Any]] = None,
    billing_issue: bool = False,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": provider_id,
        "configured": configured,
        "healthy": healthy,
        "health": health_state,
        "health_reason": health_reason,
        "is_selectable": is_selectable,
        "latency_ms": round(float(latency_ms), 1),
    }
    if circuit_breaker is not None:
        result["circuit_breaker"] = circuit_breaker
    if warmup is not None:
        result["warmup"] = warmup
    if billing_issue:
        result["billing_issue"] = billing_issue
    return result


async def _maybe_inject_test_health_check(
    dispatcher: Any,
    provider_id: str,
) -> Optional[ProviderHealth]:
    state = dispatcher._active_test_mode_state(provider_id)
    if state is None:
        return None
    profile = state["profiles"][provider_id]
    health_profile = profile.get("health_check")
    if not isinstance(health_profile, dict):
        return None
    latency_ms = float(health_profile.get("latency_ms", 0.0) or 0.0)
    if latency_ms > 0:
        await asyncio.sleep(latency_ms / 1000)
    error_message = str(health_profile.get("error", "") or "")
    healthy = bool(health_profile.get("healthy", False))
    billing_issue = bool(health_profile.get("billing_issue", False))
    return ProviderHealth(
        provider_id=provider_id,
        healthy=healthy,
        latency_ms=latency_ms,
        error=error_message or None,
        billing_issue=billing_issue,
    )


async def check_provider(
    dispatcher: Any,
    provider_id: str,
    *,
    logger: Any,
) -> Dict[str, Any]:
    """Check health for a single provider."""
    canonical_id = dispatcher._canonical_provider_id(provider_id) or provider_id
    config = dispatcher._configs.get(canonical_id, {})
    provider = dispatcher._ensure_provider(canonical_id)
    if not config:
        return _build_health_result(
            canonical_id,
            configured=False,
            healthy=False,
            health_state="unknown",
            health_reason="Unknown provider",
            is_selectable=False,
            latency_ms=0.0,
            circuit_breaker={},
            warmup=dispatcher._warmup_state_for(canonical_id),
        )
    if provider is None:
        return _build_health_result(
            canonical_id,
            configured=False,
            healthy=False,
            health_state="unknown",
            health_reason="Provider not configured",
            is_selectable=False,
            latency_ms=0.0,
            circuit_breaker={},
            warmup=dispatcher._warmup_state_for(canonical_id),
        )

    configured = dispatcher.is_configured(canonical_id)
    if not configured:
        return _build_health_result(
            canonical_id,
            configured=False,
            healthy=False,
            health_state="unknown",
            health_reason="Provider not configured",
            is_selectable=False,
            latency_ms=0.0,
            circuit_breaker=provider.circuit_status(),
            warmup=dispatcher._warmup_state_for(canonical_id),
        )

    test_health = await _maybe_inject_test_health_check(dispatcher, canonical_id)
    if test_health is not None:
        profile = dispatcher._active_test_mode_state(canonical_id) or {}
        health_profile = (
            profile.get("profiles", {})
            .get(canonical_id, {})
            .get(
                "health_check",
                {},
            )
        )
        error_category = dispatcher._provider_error_category(
            health_profile.get("error_category") if isinstance(health_profile, dict) else None,
            test_health.error or "health check failed",
        )
        billing = bool(test_health.billing_issue)
        if test_health.healthy:
            health_state = "healthy"
        elif billing:
            health_state = "billing_issue"
            provider.record_failure(
                dispatcher._sanitize_error(test_health.error or "billing issue"),
                category=ProviderErrorCategory.RATE_LIMIT,
            )
        else:
            health_state = "unhealthy"
            provider.record_failure(
                dispatcher._sanitize_error(test_health.error or "health check failed"),
                category=error_category or ProviderErrorCategory.UNKNOWN,
            )
        return _build_health_result(
            canonical_id,
            configured=True,
            healthy=test_health.healthy,
            health_state=health_state,
            health_reason=dispatcher._sanitize_error(test_health.error or ""),
            is_selectable=bool(test_health.healthy),
            latency_ms=float(test_health.latency_ms),
            circuit_breaker=provider.circuit_status(),
            warmup=dispatcher._warmup_state_for(canonical_id),
            billing_issue=billing,
        )

    timeout_ms = int(
        config.get("health_check_timeout_ms", dispatcher.DEFAULT_HEALTH_CHECK_TIMEOUT_MS),
    )
    try:
        health = await asyncio.wait_for(
            provider.health_check(),
            timeout=max(1, timeout_ms) / 1000,
        )
        billing = getattr(health, "billing_issue", False)
        if health.healthy:
            health_state = "healthy"
        elif billing:
            health_state = "billing_issue"
            provider.record_failure(
                dispatcher._sanitize_error(getattr(health, "error", "") or "billing issue"),
                category=ProviderErrorCategory.RATE_LIMIT,
            )
        else:
            health_state = "unhealthy"
        return _build_health_result(
            canonical_id,
            configured=True,
            healthy=health.healthy,
            health_state=health_state,
            health_reason=dispatcher._sanitize_error(getattr(health, "error", "") or ""),
            is_selectable=bool(health.healthy),
            latency_ms=float(health.latency_ms),
            circuit_breaker=provider.circuit_status(),
            warmup=dispatcher._warmup_state_for(canonical_id),
            billing_issue=billing,
        )
    except asyncio.TimeoutError:
        provider.record_failure(
            f"timeout after {timeout_ms}ms",
            category=ProviderErrorCategory.TIMEOUT,
        )
        return _build_health_result(
            canonical_id,
            configured=True,
            healthy=False,
            health_state="unhealthy",
            health_reason=f"timed out after {timeout_ms}ms",
            is_selectable=False,
            latency_ms=float(timeout_ms),
            circuit_breaker=provider.circuit_status(),
            warmup=dispatcher._warmup_state_for(canonical_id),
        )
    except Exception as exc:
        provider.record_failure(
            dispatcher._sanitize_error(exc),
            category=classify_provider_error(exc),
        )
        return _build_health_result(
            canonical_id,
            configured=True,
            healthy=False,
            health_state="unhealthy",
            health_reason=dispatcher._sanitize_error(exc),
            is_selectable=False,
            latency_ms=0.0,
            circuit_breaker=provider.circuit_status(),
            warmup=dispatcher._warmup_state_for(canonical_id),
        )


async def get_provider_inventory(
    dispatcher: Any,
    include_hidden: bool = False,
) -> List[Dict[str, Any]]:
    providers = dispatcher.list_providers(include_hidden=include_hidden)
    checks = await asyncio.gather(
        *(
            check_provider(dispatcher, item["id"], logger=getattr(dispatcher, "_logger", None))
            for item in providers
        ),
        return_exceptions=True,
    )
    inventory: List[Dict[str, Any]] = []
    for meta, health in zip(providers, checks):
        if isinstance(health, Exception):
            health = {
                "configured": False,
                "healthy": False,
                "health": "unknown",
                "health_reason": dispatcher._sanitize_error(health),
                "is_selectable": False,
                "latency_ms": 0.0,
            }
        inventory.append({**meta, **health})
    return inventory


async def health_all(
    dispatcher: Any,
    include_hidden: bool = False,
) -> Dict[str, Any]:
    inventory = await get_provider_inventory(dispatcher, include_hidden=include_hidden)
    return {
        item["id"]: {
            "healthy": bool(item["healthy"]),
            "configured": bool(item["configured"]),
            "health": item["health"],
            "latency_ms": item["latency_ms"],
            "error": item["health_reason"],
            "is_selectable": bool(item["is_selectable"]),
            "circuit_breaker": item.get("circuit_breaker", {}),
        }
        for item in inventory
    }
