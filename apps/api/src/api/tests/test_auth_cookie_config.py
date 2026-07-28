"""Auth cookie configuration and header behavior tests."""

from __future__ import annotations

import importlib

from fastapi import Response


def _reload_auth_modules():
    import api.auth.router.config as config_module
    import api.auth.router.cookies as cookies_module

    config = importlib.reload(config_module)
    cookies = importlib.reload(cookies_module)
    return config, cookies


def _set_cookie_headers(response: Response) -> list[str]:
    return [
        value.decode("latin-1")
        for key, value in response.raw_headers
        if key.lower() == b"set-cookie"
    ]


def _configure_env(
    monkeypatch,
    *,
    environment: str,
    cookie_samesite: str | None = None,
    cookie_secure: str | None = None,
):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("ENVIRONMENT", environment)

    if cookie_samesite is None:
        monkeypatch.delenv("AUTH_COOKIE_SAMESITE", raising=False)
    else:
        monkeypatch.setenv("AUTH_COOKIE_SAMESITE", cookie_samesite)

    if cookie_secure is None:
        monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
    else:
        monkeypatch.setenv("AUTH_COOKIE_SECURE", cookie_secure)


def test_cookie_defaults_in_development(monkeypatch):
    _configure_env(monkeypatch, environment="development")
    config, _ = _reload_auth_modules()

    assert config.COOKIE_SAMESITE == "lax"
    assert config.COOKIE_SECURE is False


def test_cookie_defaults_in_production(monkeypatch):
    _configure_env(monkeypatch, environment="production")
    config, _ = _reload_auth_modules()

    assert config.COOKIE_SAMESITE == "none"
    assert config.COOKIE_SECURE is True


def test_cookie_overrides_from_env(monkeypatch):
    _configure_env(
        monkeypatch,
        environment="production",
        cookie_samesite="strict",
        cookie_secure="false",
    )
    config, _ = _reload_auth_modules()

    assert config.COOKIE_SAMESITE == "strict"
    assert config.COOKIE_SECURE is False


def test_set_auth_cookies_uses_configured_cookie_policy(monkeypatch):
    _configure_env(
        monkeypatch,
        environment="production",
        cookie_samesite="none",
        cookie_secure="true",
    )
    _, cookies = _reload_auth_modules()

    response = Response()
    cookies._set_auth_cookies(response, "access-token", "refresh-token")
    headers = _set_cookie_headers(response)

    assert any("session_token=access-token" in header for header in headers)
    assert any("refresh_token=refresh-token" in header for header in headers)
    assert all("HttpOnly" in header for header in headers)
    assert all("Secure" in header for header in headers)
    assert all("SameSite=none" in header for header in headers)


def test_clear_auth_cookies_uses_configured_cookie_policy(monkeypatch):
    _configure_env(
        monkeypatch,
        environment="production",
        cookie_samesite="none",
        cookie_secure="true",
    )
    _, cookies = _reload_auth_modules()

    response = Response()
    cookies._clear_auth_cookies(response)
    headers = _set_cookie_headers(response)

    assert any("session_token=" in header for header in headers)
    assert any("refresh_token=" in header for header in headers)
    assert all("Secure" in header for header in headers)
    assert all("SameSite=none" in header for header in headers)
