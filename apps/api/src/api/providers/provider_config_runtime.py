"""Runtime access to the shared, validated provider TOML schema."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SCHEMA_PATH = _REPO_ROOT / "packages" / "shared" / "src" / "provider_config.py"

_SPEC = importlib.util.spec_from_file_location("provider_config", _SCHEMA_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load provider config schema: {_SCHEMA_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

ModelAlias = _MODULE.ModelAlias
ModelDefaults = _MODULE.ModelDefaults
ProviderConfig = _MODULE.ProviderConfig
ProviderToml = _MODULE.ProviderToml
invalidate_cache = _MODULE.invalidate_cache
load_provider_config = _MODULE.load_provider_config

__all__ = [
    "ModelAlias",
    "ModelDefaults",
    "ProviderConfig",
    "ProviderToml",
    "invalidate_cache",
    "load_provider_config",
]
