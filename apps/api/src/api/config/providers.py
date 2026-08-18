"""
Provider configuration — sourced from config/providers.toml (single source of truth).

Previously this module held hardcoded lists of providers and models.
Those have been migrated to config/providers.toml.
This module now reads from the TOML at runtime.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict, List


def _parse_toml(path: Path) -> dict:
    try:
        import tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        toml = importlib.import_module("toml")
        with open(path, "r", encoding="utf-8") as f:
            return toml.load(f)


def _load_toml() -> dict:
    """Load the canonical providers.toml."""
    path = Path(__file__).resolve().parents[5] / "config" / "providers.toml"
    if not path.exists():
        return {}
    try:
        return _parse_toml(path)
    except Exception:
        return {}


def get_provider_settings() -> List[Dict[str, Any]]:
    """Get provider settings from providers.toml for monitoring."""
    parsed = _load_toml()
    providers_raw = parsed.get("providers", {})
    if not isinstance(providers_raw, dict):
        return []

    result = []
    for pid, raw in providers_raw.items():
        if not isinstance(raw, dict):
            continue
        result.append(
            {
                "name": pid,
                "api_key": raw.get("api_key_env"),
                "base_url": raw.get("endpoint", ""),
                "models": list(raw.get("models", [])),
                "enabled": raw.get("is_active", True),
            }
        )

    # Also include model_defaults as model configs
    return result


def get_provider_config() -> Dict[str, Any]:
    """Get overall provider configuration."""
    parsed = _load_toml()
    health = parsed.get("default", {}).get("health", {})
    if isinstance(health, dict):
        return {
            "health_check_interval": int(health.get("health_check_interval", 60)),
            "timeout": int(health.get("timeout_seconds", 10)),
            "retry_attempts": int(health.get("retry_attempts", 3)),
        }
    return {
        "health_check_interval": 60,
        "timeout": 10,
        "retry_attempts": 3,
    }


def get_model_config(model_name: str) -> Dict[str, Any]:
    """Get configuration for a specific model from providers.toml."""
    parsed = _load_toml()
    model_defaults = parsed.get("model_defaults", {})
    if not isinstance(model_defaults, dict):
        return {}
    raw = model_defaults.get(model_name, {})
    if not isinstance(raw, dict):
        return {}
    return {
        "provider": raw.get("provider", ""),
        "max_tokens": int(raw.get("max_tokens", 4000)),
        "temperature": float(raw.get("temperature", 0.7)),
        "supports_streaming": bool(raw.get("supports_streaming", True)),
    }
