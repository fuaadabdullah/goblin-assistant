"""Self-hosted provider warmup lifecycle management."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List, Optional


def _load_prewarm_enabled() -> bool:
    return os.getenv("ENABLE_SELF_HOSTED_PREWARM", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _load_prewarm_latency_threshold_ms() -> float:
    raw_value = os.getenv("SELF_HOSTED_PREWARM_LATENCY_THRESHOLD_MS", "2500").strip()
    try:
        return max(0.0, float(raw_value))
    except (TypeError, ValueError):
        return 2500.0


def _is_self_hosted(config: Dict[str, Any]) -> bool:
    return str(config.get("tier", "")) == "self_hosted"


def _warmup_parent_id(target_id: str) -> str:
    if "." not in target_id:
        return target_id
    return target_id.split(".", 1)[0]


def update_warmup_state(
    warmup_states: Dict[str, Dict[str, Any]],
    target_id: str,
    *,
    state: str,
    latency_ms: Optional[float] = None,
    error: str = "",
) -> None:
    warmup_states[target_id] = {
        "state": state,
        "latency_ms": round(float(latency_ms), 1) if latency_ms is not None else None,
        "error": error,
        "updated_at": time.time(),
    }
    parent_id = _warmup_parent_id(target_id)
    if parent_id == target_id:
        return
    child_states = {
        key: value
        for key, value in warmup_states.items()
        if _warmup_parent_id(key) == parent_id and key != parent_id
    }
    if any(item["state"] == "warm" for item in child_states.values()):
        parent_state = "warm"
    elif any(item["state"] == "warming" for item in child_states.values()):
        parent_state = "warming"
    elif child_states and all(item["state"] == "failed" for item in child_states.values()):
        parent_state = "failed"
    else:
        parent_state = "idle"
    fastest = min(
        (
            item["latency_ms"]
            for item in child_states.values()
            if isinstance(item.get("latency_ms"), (int, float))
        ),
        default=None,
    )
    errors = [item["error"] for item in child_states.values() if item.get("error")]
    warmup_states[parent_id] = {
        "state": parent_state,
        "latency_ms": fastest,
        "error": errors[-1] if errors else "",
        "updated_at": time.time(),
        "backends": child_states,
    }


def warmup_state_for(
    warmup_states: Dict[str, Dict[str, Any]],
    provider_id: str,
) -> Dict[str, Any]:
    return dict(warmup_states.get(provider_id, {"state": "idle"}))


def is_warmup_routing_blocked(
    warmup_states: Dict[str, Dict[str, Any]],
    configs: Dict[str, Dict[str, Any]],
    provider_id: str,
) -> bool:
    config = configs.get(provider_id, {})
    if not _is_self_hosted(config):
        return False
    _ = warmup_state_for(warmup_states, provider_id)
    # Warmup is advisory only at runtime. Routing should follow provider health
    # and circuit-breaker state so a healthy self-hosted backend can serve live
    # traffic even if a prewarm probe failed or never ran.
    return False


def start_background_tasks(
    warmup_states: Dict[str, Dict[str, Any]],
    prewarm_enabled: bool,
    warmup_task_ref: List[Optional[asyncio.Task[Any]]],
    background_started_ref: List[bool],
    configs: Dict[str, Dict[str, Any]],
    ensure_provider_fn,
    is_configured_fn,
    sanitize_error_fn,
    *,
    logger: Any,
    prewarm_latency_threshold_ms: float,
) -> None:
    if background_started_ref[0]:
        return
    if not prewarm_enabled:
        background_started_ref[0] = True
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    background_started_ref[0] = True
    warmup_task_ref[0] = loop.create_task(
        _prewarm_self_hosted_providers(
            warmup_states,
            configs,
            ensure_provider_fn,
            is_configured_fn,
            sanitize_error_fn,
            logger=logger,
            prewarm_latency_threshold_ms=prewarm_latency_threshold_ms,
        )
    )


async def _prewarm_target(
    warmup_states: Dict[str, Dict[str, Any]],
    target_id: str,
    provider,
    sanitize_error_fn,
    *,
    logger: Any,
    prewarm_latency_threshold_ms: float,
) -> None:
    update_warmup_state(warmup_states, target_id, state="warming")
    started_at = time.perf_counter()
    try:
        result = await provider.warmup()
        latency_ms = (
            float(getattr(result, "latency_ms", 0.0)) or (time.perf_counter() - started_at) * 1000
        )
        final_state = "warm" if latency_ms <= prewarm_latency_threshold_ms else "warming"
        if not getattr(result, "ok", False):
            final_state = "failed"
        update_warmup_state(
            warmup_states,
            target_id,
            state=final_state,
            latency_ms=latency_ms,
            error=str(getattr(result, "error", "") or ""),
        )
    except Exception as exc:
        update_warmup_state(warmup_states, target_id, state="failed", error=str(exc))
        logger.warning("provider_prewarm_failed", provider=target_id, error=str(exc))


def note_provider_result(
    warmup_states: Dict[str, Dict[str, Any]],
    provider_id: str,
    *,
    ok: bool,
    latency_ms: float = 0.0,
    error: str = "",
    prewarm_latency_threshold_ms: float = 2500.0,
) -> None:
    update_warmup_state(
        warmup_states,
        provider_id,
        state="warm"
        if ok and latency_ms <= prewarm_latency_threshold_ms
        else ("failed" if not ok else "warming"),
        latency_ms=latency_ms,
        error=error,
    )


async def _prewarm_self_hosted_providers(
    warmup_states: Dict[str, Dict[str, Any]],
    configs: Dict[str, Dict[str, Any]],
    ensure_provider_fn,
    is_configured_fn,
    sanitize_error_fn,
    *,
    logger: Any,
    prewarm_latency_threshold_ms: float,
) -> None:
    tasks: List[asyncio.Task[Any]] = []
    for provider_id, config in configs.items():
        if provider_id == "mock" or not is_configured_fn(provider_id):
            continue
        if not _is_self_hosted(config):
            continue
        provider = ensure_provider_fn(provider_id)
        if provider is None:
            continue
        for target_id, target_provider in provider.warmup_targets():
            tasks.append(
                asyncio.create_task(
                    _prewarm_target(
                        warmup_states,
                        target_id,
                        target_provider,
                        sanitize_error_fn,
                        logger=logger,
                        prewarm_latency_threshold_ms=prewarm_latency_threshold_ms,
                    )
                )
            )
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
