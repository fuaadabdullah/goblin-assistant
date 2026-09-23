"""Tests for typed deployment configuration and error-type links."""

from __future__ import annotations

from api.config.settings import get_settings
from api.core.error_types import ErrorType, get_error_type_uri


def test_settings_reads_deployment_values(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("BACKEND_URL", "https://api.example.test")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "yes")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "17")

    settings = get_settings()

    assert settings.environment == "staging"
    assert settings.backend_url == "https://api.example.test"
    assert settings.rate_limit_enabled is True
    assert settings.rate_limit_per_minute == 17


def test_error_type_uri_uses_configured_base_url(monkeypatch):
    monkeypatch.setenv("ERROR_TYPE_BASE_URL", "https://errors.example.test/")

    assert get_error_type_uri(ErrorType.PROVIDER) == "https://errors.example.test/errors/provider"
