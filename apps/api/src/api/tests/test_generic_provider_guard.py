from __future__ import annotations

import api.providers as providers_pkg
import pytest
from api.providers.generic import GenericProvider


def test_generic_provider_is_not_exported_from_package():
    assert not hasattr(providers_pkg, "GenericProvider")
    assert "GenericProvider" not in getattr(providers_pkg, "__all__", [])


def test_generic_provider_is_blocked_outside_dev_or_test(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    GenericProvider._selection_warned = False

    with pytest.raises(RuntimeError, match="disabled outside development or test environments"):
        GenericProvider(
            "generic",
            {
                "endpoint": "http://localhost",
                "default_model": "gpt-4o-mini",
            },
        )


def test_generic_provider_allows_development_mode(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("TESTING", raising=False)
    GenericProvider._selection_warned = False

    provider = GenericProvider(
        "generic",
        {
            "endpoint": "http://localhost",
            "default_model": "gpt-4o-mini",
        },
    )

    assert provider.provider_id == "generic"
