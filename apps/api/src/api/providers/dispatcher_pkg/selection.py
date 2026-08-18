"""Provider selection owned outside the dispatcher facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(frozen=True)
class ProviderSelectionPlan:
    """Provider ordering chosen for a dispatch request."""

    explicit_mode: bool
    ordered: List[str]
    routing_mode: str


class SelectionEngine:
    """Owns provider selection and fallback ordering for dispatch execution."""

    def __init__(self, dispatcher: Any) -> None:
        self._dispatcher = dispatcher

    async def select_provider(self, providers: list, *, preferred: Optional[str] = None) -> Any:
        return await select_provider(providers, preferred=preferred)

    async def invoke_with_fallback(self, prompt: str, *, providers: list) -> Any:
        return await invoke_with_fallback(prompt, providers=providers)

    def resolve_and_order_candidates(
        self,
        resolved_pid: Optional[str],
        candidates: List[str],
    ) -> ProviderSelectionPlan:
        from ...routing.router_registry import registry

        dispatcher = self._dispatcher
        explicit_mode = resolved_pid not in (None, "auto", "cheapest", "local")
        routing_mode = "explicit" if explicit_mode else resolved_pid or "auto"
        if explicit_mode:
            first_config = dispatcher._configs.get(candidates[0], {}) if candidates else {}
            if first_config.get("force_fallback"):
                fallback_order = [p for p in dispatcher._hybrid_order() if p not in candidates]
                return ProviderSelectionPlan(
                    explicit_mode=explicit_mode,
                    ordered=[*candidates, *fallback_order],
                    routing_mode=routing_mode,
                )
            return ProviderSelectionPlan(
                explicit_mode=explicit_mode,
                ordered=candidates,
                routing_mode=routing_mode,
            )

        configured_candidates = dispatcher._auto_configured_candidates(candidates)
        if not configured_candidates:
            configured_candidates = [p for p in candidates if dispatcher.is_configured(p)]

        available: List[str] = []
        for provider_id in configured_candidates:
            current_provider = dispatcher._ensure_provider(provider_id)
            if current_provider is None:
                continue
            canary = dispatcher._is_canary_attempt(provider_id, resolved_pid)
            if current_provider.should_attempt(canary=canary) and (
                registry.get(provider_id).success_rate >= dispatcher._routing_min_success_rate
            ):
                available.append(provider_id)

        # `available` is gated by canary/health/success-rate and can be a
        # strict subset of `configured_candidates` (e.g. only one or two
        # providers pass the gate on a cold start). If every gated candidate
        # fails, still fall through to the rest of the configured list
        # instead of giving up while known-configured providers sit untried.
        rest = [p for p in configured_candidates if p not in available]
        return ProviderSelectionPlan(
            explicit_mode=explicit_mode,
            ordered=[*available, *rest] if available else configured_candidates,
            routing_mode=routing_mode,
        )

    async def apply_user_access(
        self,
        ordered: List[str],
        *,
        user_id: Any,
    ) -> List[str]:
        if not isinstance(user_id, str) or not user_id:
            return ordered

        from ..supabase_events import check_provider_access

        return [
            provider_id
            for provider_id in ordered
            if await check_provider_access(user_id, provider_id)
        ]

    def build_dry_run_response(
        self,
        ordered: List[str],
        resolved_model: Optional[str],
        explicit_mode: bool,
    ) -> dict[str, Any]:
        dispatcher = self._dispatcher
        candidate_detail = []
        for provider_id in ordered:
            current_provider = dispatcher._ensure_provider(provider_id)
            candidate_detail.append(
                {
                    "provider": provider_id,
                    "model": resolved_model or getattr(current_provider, "default_model", ""),
                    "configured": dispatcher.is_configured(provider_id),
                }
            )
        first = candidate_detail[0]
        return {
            "ok": True,
            "dry_run": True,
            "resolved_provider": first["provider"],
            "resolved_model": first["model"],
            "routing_mode": "explicit" if explicit_mode else "auto",
            "candidate_order": candidate_detail,
        }


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
        except Exception as exc:
            last_exc = exc
    raise last_exc or RuntimeError("No providers available")
