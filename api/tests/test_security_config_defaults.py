"""Security configuration default behavior tests."""

import importlib

import api.security_config as security_config_module


def _reload_security_config():
    return importlib.reload(security_config_module)


def test_security_config_production_defaults_enable_rate_limit_and_restrict_headers(
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)

    module = _reload_security_config()

    assert module.SecurityConfig.RATE_LIMIT_ENABLED is True
    assert module.SecurityConfig.ALLOWED_HEADERS == [
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-CSRF-Token",
    ]


def test_security_config_non_production_defaults_disable_rate_limit_and_allow_wildcard_headers(
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)

    module = _reload_security_config()

    assert module.SecurityConfig.RATE_LIMIT_ENABLED is False
    assert module.SecurityConfig.ALLOWED_HEADERS == ["*"]


def test_security_config_explicit_rate_limit_env_override(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")

    module = _reload_security_config()

    assert module.SecurityConfig.RATE_LIMIT_ENABLED is True
