"""
Security configuration and utilities for Goblin Assistant API
"""

import os
from typing import List


class SecurityConfig:
    """Security configuration settings"""

    # Runtime Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

    # Shared production CORS header allowlist
    PRODUCTION_ALLOWED_HEADERS = [
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-CSRF-Token",
    ]

    # CORS Configuration
    # Default to localhost for development, override in production with specific origins
    # Using wildcard (*) for headers in dev for flexibility, restrict in production
    ALLOWED_ORIGINS = (
        [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
        if os.getenv("ALLOWED_ORIGINS")
        else ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    ALLOW_CREDENTIALS = True
    ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS = (
        PRODUCTION_ALLOWED_HEADERS.copy()
        if ENVIRONMENT == "production"
        else ["*"]
    )

    # Rate Limiting
    _rate_limit_env = os.getenv("RATE_LIMIT_ENABLED")
    RATE_LIMIT_ENABLED = (
        _rate_limit_env.lower() == "true"
        if isinstance(_rate_limit_env, str)
        else ENVIRONMENT == "production"
    )
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

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
        print("🚨 SECURITY VIOLATION: Debug mode cannot be enabled in production!")
        print("   Forcing DEBUG=false for security reasons.")
        DEBUG = False

    # Secret Management
    SECRETS_BACKEND = os.getenv("SECRETS_BACKEND", "vault")
    VAULT_URL = os.getenv("VAULT_URL", "http://localhost:8200")
    VAULT_MOUNT_POINT = os.getenv("VAULT_MOUNT_POINT", "secret")

    # Database Security
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./goblin_assistant.db"
    )

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
                warnings.append(
                    "🚨 CRITICAL: No ALLOWED_ORIGINS configured for production CORS."
                )

            if not os.getenv("LOCAL_LLM_API_KEY"):
                warnings.append(
                    "🚨 CRITICAL: No LOCAL_LLM_API_KEY configured for production authentication."
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
        print("SECURITY WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("No security configuration warnings detected.")


# Initialize security warnings on import
log_security_warnings()
