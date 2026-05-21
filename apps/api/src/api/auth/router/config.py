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

# Cookie settings — secure flag only outside development so local HTTP works.
COOKIE_SECURE = os.getenv("ENVIRONMENT", "development") != "development"
COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
REFRESH_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

SESSION_CACHE_PREFIX = "auth:session"
