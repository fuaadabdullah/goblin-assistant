"""Backend verification tests — pytest replacement for verify_fixes.py.

Covers import smoke checks, security config structure, core dependency
importability, and health endpoint accessibility.
"""

import importlib

import pytest


# ---------------------------------------------------------------------------
# 1. Module import smoke tests
# ---------------------------------------------------------------------------

_CORE_MODULES = [
    "api.main",
    "api.middleware",
    "api.security_config",
    "api.storage.database",
    "api.storage.cache",
    "api.monitoring",
    "api.health",
    "api.secrets_router",
]


@pytest.mark.parametrize("module_path", _CORE_MODULES)
def test_core_module_importable(module_path):
    """Each core backend module should be importable without errors."""
    importlib.import_module(module_path)


# ---------------------------------------------------------------------------
# 2. Security configuration structure
# ---------------------------------------------------------------------------


def test_security_config_summary_has_required_keys(monkeypatch):
    """SecurityConfig.get_security_summary() must expose expected keys."""
    monkeypatch.setenv("ENVIRONMENT", "production")

    import api.security_config as sec_mod

    sec_mod = importlib.reload(sec_mod)
    summary = sec_mod.SecurityConfig.get_security_summary()

    required_keys = {
        "cors_configured",
        "rate_limiting_enabled",
        "debug_mode",
        "secrets_backend",
        "security_headers_enabled",
    }
    assert required_keys.issubset(summary.keys())


# ---------------------------------------------------------------------------
# 3. Core dependency importability
# ---------------------------------------------------------------------------

_REQUIRED_PACKAGES = ["fastapi", "uvicorn", "httpx", "pytest"]


@pytest.mark.parametrize("package", _REQUIRED_PACKAGES)
def test_required_package_importable(package):
    """Key runtime/test packages must be installed and importable."""
    importlib.import_module(package)


# ---------------------------------------------------------------------------
# 4. Health endpoint accessibility
# ---------------------------------------------------------------------------


def test_health_check_function_importable():
    """The health_check function must be importable from api.health."""
    from api.health import health_check  # noqa: F401
