"""
Sandbox service configuration — env vars, Redis/RQ connections, rate limiter, auth.
"""

import os

import redis
import rq
import structlog

from .middleware.rate_limiter import RateLimiter

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "goblin-assistant-sandbox:latest")
API_KEY = os.getenv("API_AUTH_KEY")
SANDBOX_ENABLED = os.getenv("SANDBOX_ENABLED", "false").lower() == "true"

# Use local writable directory, default to /tmp/goblin_sandbox if not specified
JOBS_DIR = os.getenv("JOBS_DIR", "/tmp/goblin_sandbox")

# ---------------------------------------------------------------------------
# Redis, RQ queue, rate limiter — module-level singletons
# ---------------------------------------------------------------------------

r = redis.from_url(REDIS_URL)
queue = rq.Queue("sandbox-jobs", connection=r)

sandbox_rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("SANDBOX_RATE_LIMIT_PER_MINUTE", "10")),
    requests_per_hour=int(os.getenv("SANDBOX_RATE_LIMIT_PER_HOUR", "100")),
)

# ---------------------------------------------------------------------------
# Ensure jobs directory exists at import time
# ---------------------------------------------------------------------------

try:
    os.makedirs(JOBS_DIR, exist_ok=True)
except PermissionError:
    _fallback = "/tmp/goblin_sandbox"
    logger.warning(
        "sandbox_jobs_dir_unwritable",
        configured_jobs_dir=JOBS_DIR,
        fallback_jobs_dir=_fallback,
    )
    JOBS_DIR = _fallback
    os.makedirs(JOBS_DIR, exist_ok=True)
