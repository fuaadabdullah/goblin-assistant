"""Canonical Goblin identity helpers.

The public Goblin catalog is product-based, while routing and persistence
often only know about departments and provider chains. These helpers keep the
write path canonical and make the read path tolerant of older department /
provider-shaped rows.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Set

from api.departments.products import get_product_info, list_products
from api.departments.registry import DEPARTMENT_REGISTRY


def normalize_goblin_id(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _mapping_lookup(metadata: Optional[Mapping[str, Any]], key: str) -> Optional[str]:
    if not isinstance(metadata, Mapping):
        return None
    return normalize_goblin_id(metadata.get(key))


def _metadata_candidates(metadata: Any) -> Set[str]:
    if not isinstance(metadata, Mapping):
        return set()

    candidates: Set[str] = set()
    for key in ("goblin_id", "goblin", "department", "provider"):
        candidate = normalize_goblin_id(metadata.get(key))
        if candidate:
            candidates.add(candidate)
    return candidates


def is_provider_identifier(value: Any) -> bool:
    normalized = normalize_goblin_id(value)
    if not normalized:
        return False

    for policy in DEPARTMENT_REGISTRY.list_policies():
        for provider_id, _model in policy.provider_chain:
            if normalize_goblin_id(provider_id) == normalized:
                return True
    return False


def resolve_goblin_id(
    *,
    metadata: Optional[Mapping[str, Any]] = None,
    department: Optional[str] = None,
    fallback: Optional[str] = None,
) -> str:
    """Resolve the Goblin identity to persist on assistant messages.

    Provider identifiers are intentionally ignored here. The result should be
    the best available public Goblin identifier, with department/fallback used
    only when the request did not supply a canonical goblin field.
    """

    for candidate in (
        _mapping_lookup(metadata, "goblin_id"),
        _mapping_lookup(metadata, "goblin"),
        _mapping_lookup(metadata, "department"),
        normalize_goblin_id(department),
        normalize_goblin_id(fallback),
        "general",
    ):
        if candidate and not is_provider_identifier(candidate):
            return candidate
    return "general"


def goblin_aliases(goblin_id: Any) -> Set[str]:
    """Return canonical and legacy aliases that should match a Goblin row."""

    normalized = normalize_goblin_id(goblin_id)
    if not normalized:
        return set()

    aliases: Set[str] = {normalized}

    product = get_product_info(normalized)
    matching_products = []
    if product is not None:
        aliases.add(product.department_id.value)
        matching_products = [
            candidate
            for candidate in list_products()
            if candidate.department_id == product.department_id
        ]
    else:
        matching_products = [
            candidate
            for candidate in list_products()
            if candidate.department_id.value == normalized
        ]
        if matching_products:
            aliases.add(normalized)

    for candidate in matching_products:
        aliases.add(candidate.product_id)

    if matching_products:
        policy = DEPARTMENT_REGISTRY.get(matching_products[0].department_id)
        for provider_id, _model in policy.provider_chain:
            provider_alias = normalize_goblin_id(provider_id)
            if provider_alias:
                aliases.add(provider_alias)

    return aliases


def is_known_goblin_identifier(goblin_id: Any) -> bool:
    """True when the identifier matches a public goblin, department, or provider alias."""

    normalized = normalize_goblin_id(goblin_id)
    if not normalized:
        return False

    if get_product_info(normalized) is not None:
        return True

    if any(candidate.department_id.value == normalized for candidate in list_products()):
        return True

    return is_provider_identifier(normalized)


def message_matches_goblin(metadata: Any, goblin_id: Any) -> bool:
    aliases = goblin_aliases(goblin_id)
    if not aliases:
        return False

    return any(candidate in aliases for candidate in _metadata_candidates(metadata))
