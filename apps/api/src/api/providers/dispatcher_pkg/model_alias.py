"""Model alias resolution and pattern matching."""

from __future__ import annotations

from typing import Any, Dict, Optional


def resolve_pattern_model_alias(
    model: str,
    patterns: list[tuple[Any, str, str]],
    expand_fn: callable,
) -> Optional[tuple[str, str]]:
    """Try to match model against regex patterns and expand template aliases.

    Returns (provider, resolved_model) if a pattern matches, None otherwise.
    """
    for compiled_pattern, provider_template, model_template in patterns:
        match = compiled_pattern.fullmatch(model)
        if match is None:
            continue
        captures = tuple(match.groups())
        provider = expand_fn(provider_template, captures).strip()
        resolved_model = expand_fn(model_template, captures).strip()
        if provider and resolved_model:
            return provider, resolved_model
    return None


def resolve_model_alias(
    provider_id: Optional[str],
    model: Optional[str],
    *,
    aliases: Dict[str, tuple[str, str]],
    patterns: list[tuple[Any, str, str]],
    canonical_fn: callable,
    expand_fn: callable,
) -> tuple[Optional[str], Optional[str]]:
    """Resolve model aliases, supporting both direct lookup and pattern matching.

    Returns (resolved_provider_id, resolved_model).
    """
    if model is None:
        return provider_id, model

    alias = aliases.get(model)
    if alias is None:
        alias = resolve_pattern_model_alias(model, patterns, expand_fn)
    if alias is None:
        return provider_id, model

    alias_provider, alias_model = alias
    alias_provider = canonical_fn(alias_provider) or alias_provider
    if provider_id in (None, "auto"):
        return alias_provider, alias_model

    canonical_id = canonical_fn(provider_id)
    if canonical_id == alias_provider:
        return canonical_id, alias_model
    return canonical_id or provider_id, model
