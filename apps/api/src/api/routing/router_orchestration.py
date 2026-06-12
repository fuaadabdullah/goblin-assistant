"""High-level routing entry points: top_providers_for, route_task, route_task_sync."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from .router_strategies import cost_router, tier_router


def _dispatcher():
    from ..providers.dispatcher import dispatcher  # noqa: PLC0415

    return dispatcher


def _provider_costs(provider_ids: List[str]) -> Dict[str, tuple[float, float]]:
    from ..providers.pricing import resolve_model_pricing  # noqa: PLC0415

    dispatch = _dispatcher()
    costs: Dict[str, tuple[float, float]] = {}
    for provider_id in provider_ids:
        provider = dispatch.get_provider(provider_id)
        pricing = resolve_model_pricing(
            provider.provider_id,
            provider.default_model or None,
            config=provider.config,
        )
        costs[provider_id] = (pricing.input_per1k, pricing.output_per1k)
    return costs


def top_providers_for(
    capability: str,
    prefer_local: bool = False,
    prefer_cost: bool = False,
    limit: int = 6,
) -> List[str]:
    dispatch = _dispatcher()
    candidates = dispatch.top_providers_for(
        capability,
        prefer_local=prefer_local,
        prefer_cost=prefer_cost,
        limit=max(1, limit),
    )
    if not candidates:
        return []

    if prefer_cost:
        ranked = cost_router.rank(candidates, _provider_costs(candidates))
        return ranked[: max(1, limit)]

    if prefer_local:
        local_candidates = [
            pid for pid in tier_router.providers_for_tier("local") if pid in candidates
        ]
        return local_candidates[: max(1, limit)]

    return candidates[: max(1, limit)]


async def route_task(
    task_type: str,
    payload: Dict[str, Any],
    prefer_local: bool = False,
    prefer_cost: bool = False,
    max_retries: int = 2,
    stream: bool = False,
) -> Dict[str, Any]:
    dispatch = _dispatcher()
    candidates = top_providers_for(
        capability=task_type,
        prefer_local=prefer_local,
        prefer_cost=prefer_cost,
        limit=max(1, max_retries + 1),
    )
    if not candidates:
        return {"ok": False, "error": "no providers available", "providers_tried": []}

    last_error = "Routing failed"
    for provider_id in candidates:
        result = await dispatch.invoke_provider(
            provider_id=provider_id,
            model=(payload.get("model") if isinstance(payload.get("model"), str) else None),
            payload=payload,
            timeout_ms=int(payload.get("timeout_ms", 30000)),
            stream=stream,
        )
        if isinstance(result, dict) and result.get("ok"):
            result.setdefault("selected_provider", provider_id)
            return result
        if isinstance(result, dict):
            last_error = str(result.get("error", last_error))

    return {"ok": False, "error": last_error, "providers_tried": candidates}


def route_task_sync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    try:
        asyncio.get_running_loop()
        return {
            "ok": False,
            "error": "route_task_sync cannot run inside an active event loop",
        }
    except RuntimeError:
        return asyncio.run(route_task(*args, **kwargs))
