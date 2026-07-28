from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import api.routing.health_provider as health_provider_module
from api.routing.health_provider import CachedProviderHealthProvider, StaticHealthProvider


def test_static_health_provider_defaults_missing_providers_to_available():
    provider = StaticHealthProvider({"anthropic": False})

    availability = provider.availability_for(["openai", "anthropic"])

    assert availability == {"openai": True, "anthropic": False}


def test_cached_health_provider_reads_cached_status_without_availability_fallback(monkeypatch):
    monitor = MagicMock()
    monitor.get_all_status.return_value = {
        "openai": {"configured": True, "status": "healthy"},
        "anthropic": {"configured": True, "status": "unhealthy"},
        "gemini": {"configured": False, "status": "healthy"},
    }
    module = SimpleNamespace(health_monitor=monitor)
    monkeypatch.setattr(
        health_provider_module.importlib,
        "import_module",
        lambda _name: module,
    )

    availability = CachedProviderHealthProvider().availability_for(
        ["openai", "anthropic", "gemini", "unknown"]
    )

    assert availability == {
        "openai": True,
        "anthropic": False,
        "gemini": False,
        "unknown": True,
    }
    monitor.get_all_status.assert_called_once_with(include_hidden=False)
    monitor.is_available.assert_not_called()
