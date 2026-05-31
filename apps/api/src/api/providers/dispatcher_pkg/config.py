from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..provider_config_runtime import ProviderToml, load_provider_config
from ..provider_registry import ProviderRuntimeConfig

ModelAliasPatternRule = tuple[re.Pattern[str], str, str]


def normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def load_provider_toml(*, logger: Any) -> Optional[ProviderToml]:
    try:
        return load_provider_config(use_cache=True)
    except Exception as exc:
        logger.warning("provider_config_load_failed", error=str(exc))
        return None


def compile_wildcard_alias_pattern(pattern: str) -> re.Pattern[str]:
    regex_parts: List[str] = []
    for char in pattern:
        if char == "*":
            regex_parts.append("(.+?)")
        else:
            regex_parts.append(re.escape(char))
    return re.compile("^" + "".join(regex_parts) + "$")


def expand_alias_template(template: str, captures: tuple[str, ...]) -> str:
    if not captures:
        return template

    expanded = template.replace("{*}", captures[0])
    for idx, capture in enumerate(captures, start=1):
        expanded = expanded.replace(f"{{{idx}}}", capture)

    if "*" not in expanded:
        return expanded

    parts = expanded.split("*")
    out = parts[0]
    for idx, tail in enumerate(parts[1:], start=1):
        capture = captures[min(idx - 1, len(captures) - 1)]
        out += capture + tail
    return out


def load_toml_providers(
    provider_toml: Optional[ProviderToml],
    *,
    logger: Any,
) -> Dict[str, Dict[str, Any]]:
    if provider_toml is None:
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for provider_id, provider_cfg in provider_toml.providers.items():
        try:
            runtime_cfg = ProviderRuntimeConfig.from_source(
                provider_id,
                provider_cfg.model_dump(),
            )
            result[provider_id] = runtime_cfg.to_provider_dict()
        except (TypeError, ValueError) as exc:
            logger.warning(
                "provider_config_invalid",
                provider=provider_id,
                error=str(exc),
            )
    return result


def load_aliases(provider_toml: Optional[ProviderToml]) -> Dict[str, str]:
    if provider_toml is None:
        return {}
    normalized: Dict[str, str] = {}
    for alias, target in provider_toml.provider_aliases.items():
        normalized[normalize_token(alias)] = normalize_token(target)
    return normalized


def load_model_aliases(
    provider_toml: Optional[ProviderToml],
) -> tuple[Dict[str, tuple[str, str]], List[ModelAliasPatternRule]]:
    if provider_toml is None:
        return {}, []

    exact_aliases: Dict[str, tuple[str, str]] = {}
    patterns: List[ModelAliasPatternRule] = []

    for alias, val in provider_toml.model_aliases.items():
        provider = str(val.provider or "").strip()
        model = str(val.model or "").strip()
        if not provider or not model:
            continue
        if "*" in alias:
            patterns.append((compile_wildcard_alias_pattern(alias), provider, model))
        else:
            exact_aliases[alias] = (provider, model)

    return exact_aliases, patterns


def load_visible_providers(provider_toml: Optional[ProviderToml]) -> List[str]:
    if provider_toml is None:
        return []
    ordered: List[str] = []
    seen: set[str] = set()
    for entry in provider_toml.visible_providers:
        normalized = normalize_token(entry)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered

