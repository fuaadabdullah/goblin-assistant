from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from ..ops.security import require_ops_access
from ..providers.dispatcher import dispatcher
from ..providers.quota_service import quota_service

router = APIRouter()


def _provider_models(entry: Dict[str, Any]) -> List[str]:
    models = [str(model).strip() for model in entry.get("models", []) if str(model).strip()]
    default_model = str(entry.get("default_model", "")).strip()
    if default_model and default_model not in models:
        models.insert(0, default_model)
    return list(dict.fromkeys(models))


def _preferred_snapshot_model(entry: Dict[str, Any]) -> Optional[str]:
    default_model = str(entry.get("default_model", "")).strip()
    if default_model:
        return default_model
    models = _provider_models(entry)
    return models[0] if models else None


def _derive_skip_reason(
    *,
    provider: Any,
    entry: Dict[str, Any],
    circuit: Dict[str, Any],
    warmup: Dict[str, Any],
    quota: Dict[str, Any],
) -> Optional[str]:
    if not bool(entry.get("configured")):
        return "not_configured"

    if (
        str(warmup.get("state", "idle")) in {"warming", "failed"}
        and str(entry.get("tier")) == "self_hosted"
    ):
        return f"warmup_{warmup.get('state')}"

    circuit_state = str(circuit.get("state", "")).lower()
    if circuit_state in {"soft_open", "hard_open"} or not bool(circuit.get("available", True)):
        return "circuit_open"

    provider_scope = quota.get("provider_scope", {})
    model_scope = quota.get("model_scope", {})
    provider_requests = provider_scope.get("remaining_requests")
    provider_tokens = provider_scope.get("remaining_tokens")
    model_requests = model_scope.get("remaining_requests")
    model_tokens = model_scope.get("remaining_tokens")

    if any(
        value == 0
        for value in (provider_requests, provider_tokens, model_requests, model_tokens)
        if value is not None
    ):
        return "quota_exhausted"

    if not bool(provider.should_attempt(canary=False)):
        return "not_routable"

    return None


async def _build_provider_state() -> Dict[str, Any]:
    debug_info = dispatcher.debug_info()
    routing_table = list(debug_info.get("routing_table", []))
    provider_state: Dict[str, Dict[str, Any]] = {}

    for entry in routing_table:
        provider_id = str(entry.get("provider_id", "")).strip()
        if not provider_id:
            continue

        warmup = dict(entry.get("warmup", {}))
        registry_stats = dict(debug_info.get("registry_stats", {}).get(provider_id, {}))
        registry_metrics = dict(
            debug_info.get("registry_metrics", {}).get("providers", {}).get(provider_id, {})
        )
        snapshot_model = _preferred_snapshot_model(entry)
        try:
            provider = dispatcher.get_provider(provider_id)
            circuit = provider.circuit_status()
            quota = await quota_service.snapshot_provider(provider_id, snapshot_model)
            skip_reason = _derive_skip_reason(
                provider=provider,
                entry=entry,
                circuit=circuit,
                warmup=warmup,
                quota=quota,
            )
        except Exception as exc:
            provider_state[provider_id] = {
                **entry,
                "registry_stats": registry_stats,
                "registry_metrics": registry_metrics,
                "warmup": warmup,
                "quota": {},
                "can_route": False,
                "skip_reason": "provider_unavailable",
                "error": str(exc),
            }
            continue

        provider_state[provider_id] = {
            **entry,
            "circuit_breaker": circuit,
            "registry_stats": registry_stats,
            "registry_metrics": registry_metrics,
            "warmup": warmup,
            "quota": quota,
            "can_route": skip_reason is None,
            "skip_reason": skip_reason,
        }

    summary = {
        "total_providers": len(provider_state),
        "configured_providers": len(
            [item for item in provider_state.values() if item.get("configured")]
        ),
        "routing_providers": len(
            [item for item in provider_state.values() if item.get("can_route")]
        ),
        "warming_providers": len(
            [
                item
                for item in provider_state.values()
                if str(item.get("warmup", {}).get("state", "")).lower() == "warming"
            ]
        ),
        "failed_warmups": len(
            [
                item
                for item in provider_state.values()
                if str(item.get("warmup", {}).get("state", "")).lower() == "failed"
            ]
        ),
        "open_circuit_breakers": len(
            [
                item
                for item in provider_state.values()
                if str(item.get("circuit_breaker", {}).get("state", "")).lower()
                in {"soft_open", "hard_open"}
            ]
        ),
        "quota_blocked": len(
            [
                item
                for item in provider_state.values()
                if item.get("skip_reason") == "quota_exhausted"
            ]
        ),
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dispatcher": debug_info,
        "providers": provider_state,
        "summary": summary,
        "routing_table": list(provider_state.values()),
    }


@router.get("/providers/state", include_in_schema=False)
@require_ops_access("read")
async def get_provider_state(request: Request) -> Dict[str, Any]:
    _ = request
    try:
        return await _build_provider_state()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Provider state failed: {exc}") from exc


__all__ = ["router", "get_provider_state"]
