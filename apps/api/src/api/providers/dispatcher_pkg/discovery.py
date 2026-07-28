"""Provider listing, capability queries, and config access."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def build_provider_list(
    dispatcher: Any,
    canonical_fn: Callable[[Optional[str]], Optional[str]],
    visible_ids: List[str],
    include_hidden: bool = False,
) -> List[Dict[str, Any]]:
    """Build the full provider metadata list from config."""
    if include_hidden or dispatcher._using_custom_configs or not visible_ids:
        provider_ids = list(dispatcher._configs.keys())
    else:
        provider_ids = []
        seen: set[str] = set()
        for entry in visible_ids:
            canonical_id = canonical_fn(entry) or entry
            if canonical_id not in dispatcher._configs or canonical_id in seen:
                continue
            seen.add(canonical_id)
            provider_ids.append(canonical_id)

    providers: List[Dict[str, Any]] = []
    for provider_id in provider_ids:
        runtime_cfg = dispatcher._runtime_config(provider_id)
        config = (
            runtime_cfg.to_provider_dict()
            if runtime_cfg is not None
            else dict(dispatcher._configs.get(provider_id, {}))
        )
        if config.get("hidden") and not include_hidden:
            continue
        providers.append(
            {
                "id": provider_id,
                "name": config.get("name", provider_id),
                "endpoint": config.get("endpoint", ""),
                "endpoint_env": config.get("endpoint_env"),
                "api_key_env": config.get("api_key_env"),
                "default_model": config.get("default_model", ""),
                "models": list(config.get("models", [])),
                "capabilities": list(config.get("capabilities", [])),
                "priority_tier": int(config.get("priority_tier", 999)),
                "tier": config.get("tier", "cloud"),
                "local_routing": bool(config.get("local_routing", False)),
                "hidden": bool(config.get("hidden", False)),
            }
        )
    return providers


def list_providers(
    dispatcher: Any,
    canonical_fn: Callable[[Optional[str]], Optional[str]],
    visible_ids: List[str],
    include_hidden: bool = False,
) -> List[Dict[str, Any]]:
    """Return a sorted, cached provider list."""
    cached = dispatcher._provider_list_cache.get(include_hidden)
    if cached is not None:
        return [dict(item) for item in cached]

    providers = dispatcher._build_provider_list(include_hidden=include_hidden)
    if include_hidden or dispatcher._using_custom_configs or not visible_ids:
        providers.sort(
            key=lambda item: (
                int(item.get("priority_tier", 999)),
                str(item.get("id", "")),
            )
        )
    dispatcher._provider_list_cache[include_hidden] = [dict(item) for item in providers]
    return [dict(item) for item in providers]


def is_configured(
    dispatcher: Any,
    canonical_fn: Callable[[Optional[str]], Optional[str]],
    provider_id: str,
) -> bool:
    canonical_id = canonical_fn(provider_id) or provider_id
    runtime_cfg = dispatcher._runtime_config(canonical_id)
    return runtime_cfg.is_configured() if runtime_cfg is not None else False


def get_provider(
    dispatcher: Any,
    canonical_fn: Callable[[Optional[str]], Optional[str]],
    provider_id: str,
) -> Any:
    canonical_id = canonical_fn(provider_id) or provider_id
    provider = dispatcher._ensure_provider(canonical_id)
    if provider is None:
        raise KeyError(f"Unknown provider: {provider_id}")
    return provider


def get_provider_config(
    dispatcher: Any,
    canonical_fn: Callable[[Optional[str]], Optional[str]],
    provider_id: str,
) -> Dict[str, Any]:
    canonical_id = canonical_fn(provider_id) or provider_id
    return dict(dispatcher._configs.get(canonical_id, {}))
