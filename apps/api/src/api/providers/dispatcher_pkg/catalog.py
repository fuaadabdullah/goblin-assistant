"""Provider catalog loading and runtime mutation helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class ProviderCatalog:
    provider_toml: Any
    provider_configs: Dict[str, Dict[str, Any]]
    provider_aliases: Dict[str, str]
    model_aliases: Dict[str, tuple[str, str]]
    model_alias_patterns: List[Any]
    visible_provider_ids: List[str]


def load_provider_catalog(
    *,
    load_provider_toml_fn: Callable[..., Any],
    load_toml_providers_fn: Callable[..., Dict[str, Dict[str, Any]]],
    load_aliases_fn: Callable[[Any], Dict[str, str]],
    load_model_aliases_fn: Callable[[Any], tuple[Dict[str, tuple[str, str]], List[Any]]],
    load_visible_providers_fn: Callable[[Any], List[str]],
    validate_model_alias_targets_fn: Callable[..., None],
    logger: Any,
) -> ProviderCatalog:
    provider_toml = load_provider_toml_fn(logger=logger)
    provider_configs = load_toml_providers_fn(provider_toml, logger=logger)
    provider_aliases = load_aliases_fn(provider_toml)
    model_aliases, model_alias_patterns = load_model_aliases_fn(provider_toml)
    visible_provider_ids = load_visible_providers_fn(provider_toml)
    validate_model_alias_targets_fn(
        provider_toml=provider_toml,
        provider_configs=provider_configs,
        logger=logger,
    )
    return ProviderCatalog(
        provider_toml=provider_toml,
        provider_configs=provider_configs,
        provider_aliases=provider_aliases,
        model_aliases=model_aliases,
        model_alias_patterns=model_alias_patterns,
        visible_provider_ids=visible_provider_ids,
    )


def canonical_provider_id(
    value: Optional[str],
    *,
    aliases: Dict[str, str],
    normalize_fn: Callable[[str], str],
) -> Optional[str]:
    if value is None:
        return None
    normalized = normalize_fn(value)
    if not normalized:
        return None
    return aliases.get(normalized, normalized)


def invalidate_provider_runtime(dispatcher: Any, provider_id: str) -> None:
    dispatcher._providers.pop(provider_id, None)
    dispatcher._provider_list_cache.clear()
    dispatcher._warmup_states.pop(provider_id, None)


def update_backend_endpoint(
    dispatcher: Any,
    provider_id: str,
    engine: str,
    new_endpoint: str,
    *,
    canonical_fn: Callable[[str], Optional[str]],
    logger: Any,
) -> None:
    canonical_id = canonical_fn(provider_id) or provider_id
    resolved_id = canonical_id if canonical_id in dispatcher._configs else provider_id
    if resolved_id not in dispatcher._configs:
        raise KeyError(f"Unknown provider: {provider_id!r}")

    backends = dispatcher._configs[resolved_id].get("backends", [])
    for backend in backends:
        if backend.get("engine") == engine:
            backend["endpoint"] = new_endpoint
            endpoint_env = str(backend.get("endpoint_env", "") or "").strip()
            if endpoint_env:
                os.environ[endpoint_env] = new_endpoint
            break
    else:
        raise KeyError(f"No backend engine {engine!r} in {provider_id!r}")

    invalidate_provider_runtime(dispatcher, resolved_id)
    logger.info(
        "backend_endpoint_updated",
        provider=resolved_id,
        engine=engine,
        endpoint=new_endpoint,
    )


def update_provider_endpoint(
    dispatcher: Any,
    provider_id: str,
    new_endpoint: str,
    *,
    canonical_fn: Callable[[str], Optional[str]],
    logger: Any,
) -> None:
    canonical_id = canonical_fn(provider_id) or provider_id
    resolved_id = canonical_id if canonical_id in dispatcher._configs else provider_id
    if resolved_id not in dispatcher._configs:
        raise KeyError(f"Unknown provider: {provider_id!r}")

    dispatcher._configs[resolved_id]["endpoint"] = new_endpoint
    endpoint_env = str(dispatcher._configs[resolved_id].get("endpoint_env", "") or "").strip()
    if endpoint_env:
        os.environ[endpoint_env] = new_endpoint

    invalidate_provider_runtime(dispatcher, resolved_id)
    logger.info("provider_endpoint_updated", provider=resolved_id, endpoint=new_endpoint)


def apply_reloaded_catalog(
    dispatcher: Any,
    *,
    provider_configs: Dict[str, Dict[str, Any]],
    provider_toml: Any,
    load_circuit_canary_percent_fn: Callable[[Any], float],
    logger: Any,
) -> None:
    dispatcher._configs = provider_configs
    dispatcher._circuit_canary_percent = load_circuit_canary_percent_fn(provider_toml)
    dispatcher._providers.clear()
    dispatcher._provider_list_cache.clear()
    dispatcher._warmup_states.clear()
    dispatcher._background_started = False
    logger.info("provider_catalog_reloaded")


def reload_provider_catalog(
    dispatcher: Any,
    *,
    load_provider_toml_fn: Callable[..., Any],
    load_toml_providers_fn: Callable[..., Dict[str, Dict[str, Any]]],
    load_aliases_fn: Callable[[Any], Dict[str, str]],
    load_model_aliases_fn: Callable[[Any], tuple[Dict[str, tuple[str, str]], List[Any]]],
    load_visible_providers_fn: Callable[[Any], List[str]],
    validate_model_alias_targets_fn: Callable[..., None],
    load_circuit_canary_percent_fn: Callable[[Any], float],
    logger: Any,
) -> ProviderCatalog:
    catalog = load_provider_catalog(
        load_provider_toml_fn=load_provider_toml_fn,
        load_toml_providers_fn=load_toml_providers_fn,
        load_aliases_fn=load_aliases_fn,
        load_model_aliases_fn=load_model_aliases_fn,
        load_visible_providers_fn=load_visible_providers_fn,
        validate_model_alias_targets_fn=validate_model_alias_targets_fn,
        logger=logger,
    )
    apply_reloaded_catalog(
        dispatcher,
        provider_configs=catalog.provider_configs,
        provider_toml=catalog.provider_toml,
        load_circuit_canary_percent_fn=load_circuit_canary_percent_fn,
        logger=logger,
    )
    dispatcher._provider_aliases = catalog.provider_aliases
    dispatcher._model_aliases = catalog.model_aliases
    dispatcher._model_alias_patterns = catalog.model_alias_patterns
    dispatcher._visible_provider_ids = catalog.visible_provider_ids
    return catalog
