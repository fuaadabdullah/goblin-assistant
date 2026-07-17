"""Runtime loader for the shared API route contract."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONTRACT_PATH = _REPO_ROOT / "packages" / "shared" / "src" / "api_routes.py"

_SPEC = importlib.util.spec_from_file_location("api_routes", _CONTRACT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load shared API route contract: {_CONTRACT_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

API_PREFIX = _MODULE.API_PREFIX
API_VERSION = _MODULE.API_VERSION
API_V1_PREFIX = _MODULE.API_V1_PREFIX
ROUTE_PREFIXES = _MODULE.ROUTE_PREFIXES
V1_CHAT_PREFIX = _MODULE.V1_CHAT_PREFIX
V1_AUTH_PREFIX = _MODULE.V1_AUTH_PREFIX
V1_PROVIDERS_PREFIX = _MODULE.V1_PROVIDERS_PREFIX
V1_HEALTH_PREFIX = _MODULE.V1_HEALTH_PREFIX
V1_SETTINGS_PREFIX = _MODULE.V1_SETTINGS_PREFIX
build_versioned_path = _MODULE.build_versioned_path

__all__ = [
    "API_PREFIX",
    "API_VERSION",
    "API_V1_PREFIX",
    "ROUTE_PREFIXES",
    "V1_CHAT_PREFIX",
    "V1_AUTH_PREFIX",
    "V1_PROVIDERS_PREFIX",
    "V1_HEALTH_PREFIX",
    "V1_SETTINGS_PREFIX",
    "build_versioned_path",
]
