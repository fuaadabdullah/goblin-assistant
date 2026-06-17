import os


def pytest_configure(config):
    """Set required env vars before any test module is collected.

    auth.router.config raises ValueError at import time if JWT_SECRET_KEY is
    absent, so we must set a dummy before pytest imports any test file that
    does 'from api.main import app' at module level.
    """
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-pytest-only-not-for-production")
    os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
