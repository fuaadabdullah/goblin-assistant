"""
Security configuration and utilities for Goblin Assistant API
"""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)


DEFAULT_LOCAL_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
]

CANONICAL_PUBLIC_ORIGINS = [
    "https://goblin-assistant.vercel.app",
    "https://goblin-backend-dt30.onrender.com",
]

PRODUCTION_ALLOWED_HEADERS = [
    "Accept",
    "Accept-Language",
    "Content-Language",
    "Content-Type",
    "Authorization",
    "X-API-Key",
    "X-CSRF-Token",
]


def _dedupe_origins(origins: List[str]) -> List[str]:
    """Normalize, trim, and de-duplicate origins while preserving order."""
    seen = set()
    result: List[str] = []
    for origin in origins:
        normalized = origin.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def build_allowed_origins(environment: str, raw_origins: str) -> List[str]:
    """
    Build allowed CORS origins with canonical/public fallback behavior.

    This compatibility helper is intentionally explicit for tests and callers
    that validate production/development CORS policy assembly.
    """
    parsed_custom = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    if environment == "production":
        dynamic = _dedupe_origins(
            [
                os.getenv("FRONTEND_URL", ""),
                os.getenv("BACKEND_URL", ""),
            ]
        )
        return _dedupe_origins(parsed_custom + dynamic + CANONICAL_PUBLIC_ORIGINS)

    return _dedupe_origins(parsed_custom + DEFAULT_LOCAL_ORIGINS + CANONICAL_PUBLIC_ORIGINS)


def _resolve_origins(environment: str) -> List[str]:
    """
    Resolve CORS origins based on environment.

    For production, only CANONICAL_PUBLIC_ORIGINS are allowed.
    For development, local origins are used.

    This logic ensures production does not accidentally allow
    development-only origins.
    """
    custom = os.getenv("ALLOWED_ORIGINS", "")
    return build_allowed_origins(environment=environment, raw_origins=custom)


def _resolve_auth_cookie_samesite(environment: str) -> str:
    """
    Resolve the SameSite setting for auth cookies based on environment.

    In production with cross-site frontend/backend, this must be 'none'
    so the cookie is sent on cross-site requests.
    In development, 'lax' is preferred for CSRF protection.
    """
    if environment == "production":
        return os.getenv("AUTH_COOKIE_SAMESITE", "none")
    return os.getenv("AUTH_COOKIE_SAMESITE", "lax")


def _resolve_rate_limit_enabled(environment: str) -> bool:
    """Default rate limiting on in production, off elsewhere unless overridden."""
    raw = os.getenv("RATE_LIMIT_ENABLED")
    if raw is not None:
        return raw.lower() == "true"
    return environment == "production"


def _resolve_allowed_headers(environment: str) -> List[str]:
    """Keep non-production permissive while production stays explicit."""
    if environment == "production":
        return list(PRODUCTION_ALLOWED_HEADERS)
    return ["*"]


def _is_cross_site_frontend_backend() -> bool:
    """
    Heuristic: if the frontend and backend are served from different
    origins (e.g. Vercel frontend + Render backend), we consider
    the deployment cross-site.
    """
    env = os.getenv("ENVIRONMENT", "development")
    if env != "production":
        return False
    # In production, frontend & backend are different origins
    return True


class SecurityConfig:
    """
    Centralized security configuration.

    All security-sensitive settings are resolved once on import and
    should not be mutated at runtime.
    """

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    # CORS Configuration - resolved via helper
    ALLOWED_ORIGINS = _resolve_origins(ENVIRONMENT)
    ALLOWED_HEADERS = _resolve_allowed_headers(ENVIRONMENT)

    # Rate Limiting
    RATE_LIMIT_ENABLED = _resolve_rate_limit_enabled(ENVIRONMENT)
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

    # Security Headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }

    # Debug Mode - STRICTLY DISABLED IN PRODUCTION
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Override debug mode based on environment
    if ENVIRONMENT == "production" and DEBUG:
        logger.warning(
            "Security violation: Debug mode cannot be enabled in production! Forcing DEBUG=false."
        )
        DEBUG = False

    # Secret Management
    SECRETS_BACKEND = os.getenv("SECRETS_BACKEND", "vault")
    VAULT_URL = os.getenv("VAULT_URL", "http://localhost:8200")
    VAULT_MOUNT_POINT = os.getenv("VAULT_MOUNT_POINT", "secret")

    # Database Security
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./goblin_assistant.db")

    # Redis Security
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate security configuration and return warnings"""
        warnings = []
        environment = cls.ENVIRONMENT

        # Check for production security issues
        if "*" in cls.ALLOWED_ORIGINS:
            if environment == "production":
                warnings.append(
                    "🚨 CRITICAL: CORS allows all origins (*) in production! Set specific ALLOWED_ORIGINS."
                )
            else:
                warnings.append(
                    "⚠️  WARNING: CORS allows all origins (*) - acceptable for development only."
                )

        if environment == "production":
            if cls.DEBUG:
                warnings.append(
                    "🚨 CRITICAL: Debug mode is enabled in production! Set DEBUG=false."
                )

            if not os.getenv("ALLOWED_ORIGINS"):
                warnings.append("🚨 CRITICAL: No ALLOWED_ORIGINS configured for production CORS.")

            if not os.getenv("LOCAL_LLM_API_KEY"):
                warnings.append(
                    "🚨 CRITICAL: No LOCAL_LLM_API_KEY configured for production authentication."
                )

            auth_cookie_samesite = _resolve_auth_cookie_samesite(environment)
            if _is_cross_site_frontend_backend() and auth_cookie_samesite != "none":
                warnings.append(
                    "🚨 CRITICAL: Cross-site frontend/backend detected but AUTH_COOKIE_SAMESITE is not 'none'."
                )

        if "password" in cls.DATABASE_URL.lower():
            warnings.append(
                "⚠️  WARNING: Database URL contains password. Ensure this is not logged."
            )

        if "@" in cls.REDIS_URL and "redis://" in cls.REDIS_URL:
            warnings.append(
                "⚠️  WARNING: Redis URL contains credentials. Consider using Redis AUTH."
            )

        # Check for missing security environment variables in production
        if environment == "production":
            required_production_vars = ["JWT_SECRET_KEY", "DATABASE_URL"]
            for var in required_production_vars:
                if not os.getenv(var):
                    warnings.append(
                        f"🚨 CRITICAL: Required production environment variable {var} is not set."
                    )

        return warnings

    @classmethod
    def get_security_summary(cls) -> dict:
        """Get a summary of security configuration"""
        return {
            "cors_configured": len(cls.ALLOWED_ORIGINS) > 0,
            "rate_limiting_enabled": cls.RATE_LIMIT_ENABLED,
            "debug_mode": cls.DEBUG,
            "secrets_backend": cls.SECRETS_BACKEND,
            "security_headers_enabled": len(cls.SECURITY_HEADERS) > 0,
            "warnings": cls.validate_config(),
        }


def log_security_warnings():
    """Log security configuration warnings"""
    warnings = SecurityConfig.validate_config()
    if warnings:
        logger.warning("Security configuration warnings detected:")
        for warning in warnings:
            logger.warning("  - %s", warning)
    else:
        logger.info("No security configuration warnings detected.")


# Initialize security warnings on import
log_security_warnings()
