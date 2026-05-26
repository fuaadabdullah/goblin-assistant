from __future__ import annotations

import importlib

from api.security_config import _dedupe_origins, build_allowed_origins


def test_dedupe_origins_trims_and_removes_duplicates():
    origins = _dedupe_origins(
        [
            " https://example.com ",
            "",
            "https://example.com",
            "http://localhost:3000",
            "http://localhost:3000 ",
        ]
    )

    assert origins == ["https://example.com", "http://localhost:3000"]


def test_build_allowed_origins_keeps_public_frontend_in_development():
    origins = build_allowed_origins(environment="development", raw_origins="")

    assert "https://goblin-assistant.vercel.app" in origins
    assert "https://goblin-backend-dt30.onrender.com" in origins
    assert "http://localhost:3000" in origins


def test_build_allowed_origins_appends_canonical_public_origins():
    origins = build_allowed_origins(
        environment="development",
        raw_origins="https://example.com",
    )

    assert origins[0] == "https://example.com"
    assert "https://goblin-assistant.vercel.app" in origins
    assert "https://goblin-backend-dt30.onrender.com" in origins


def test_build_allowed_origins_uses_dynamic_env_origins(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://frontend.example.com")
    monkeypatch.setenv("BACKEND_URL", "https://backend.example.com")

    origins = build_allowed_origins(environment="production", raw_origins="")

    assert "https://frontend.example.com" in origins
    assert "https://backend.example.com" in origins
    assert "https://goblin-assistant.vercel.app" in origins


def test_security_config_validate_config_reports_missing_prod_settings(
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("LOCAL_LLM_API_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import api.security_config as security_config

    importlib.reload(security_config)

    warnings = security_config.SecurityConfig.validate_config()

    assert any("No ALLOWED_ORIGINS" in warning for warning in warnings)
    assert any("No LOCAL_LLM_API_KEY" in warning for warning in warnings)
    assert any("JWT_SECRET_KEY" in warning for warning in warnings)


def test_security_config_get_security_summary_contains_expected_keys(
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", "development")

    import api.security_config as security_config

    importlib.reload(security_config)

    summary = security_config.SecurityConfig.get_security_summary()

    assert summary["cors_configured"] is True
    assert "warnings" in summary
    assert "security_headers_enabled" in summary


def test_security_config_warns_when_cross_site_cookie_is_not_none(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://goblin-assistant.vercel.app")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "test-local-llm-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    monkeypatch.setenv("FRONTEND_URL", "https://goblin-assistant.vercel.app")
    monkeypatch.setenv("BACKEND_URL", "https://goblin-backend-dt30.onrender.com")
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "lax")

    import api.security_config as security_config

    importlib.reload(security_config)
    warnings = security_config.SecurityConfig.validate_config()

    assert any(
        "Cross-site frontend/backend detected but AUTH_COOKIE_SAMESITE is not 'none'."
        in warning
        for warning in warnings
    )
