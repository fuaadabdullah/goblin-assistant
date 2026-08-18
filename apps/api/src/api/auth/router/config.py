"""Auth configuration: JWT keys, expiration windows, cookie defaults."""

import os
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()


def _parse_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} must be one of: true/false, 1/0, yes/no, on/off")


def _resolve_cookie_samesite(
    environment: str,
) -> Literal["lax", "strict", "none"]:
    default_samesite = "none" if environment == "production" else "lax"
    configured = os.getenv("AUTH_COOKIE_SAMESITE", default_samesite).strip().lower()

    if configured == "lax":
        return "lax"
    if configured == "strict":
        return "strict"
    if configured == "none":
        return "none"

    raise ValueError("AUTH_COOKIE_SAMESITE must be one of: lax, strict, none")


# Cookie settings:
# - production defaults to cross-site compatible cookies for Vercel<->Render.
# - development keeps local HTTP ergonomics.
COOKIE_SAMESITE: Literal["lax", "strict", "none"] = _resolve_cookie_samesite(ENVIRONMENT)
COOKIE_SECURE = _parse_bool_env("AUTH_COOKIE_SECURE", default=ENVIRONMENT == "production")
REFRESH_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

SESSION_CACHE_PREFIX = "auth:session"
