"""Middleware package for Goblin Assistant API."""

import logging

from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Import middleware classes from the api/middleware.py file (sibling to this package)
# We need to use importlib because Python prioritizes the package over the .py file
try:
    import importlib.util
    from pathlib import Path

    # Get path to middleware.py file (sibling to middleware/ directory)
    middleware_py_path = Path(__file__).parent.parent / "middleware.py"

    if middleware_py_path.exists():
        # Load the module from the file
        spec = importlib.util.spec_from_file_location("api_middleware_file", middleware_py_path)
        middleware_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(middleware_module)

        # Extract the classes
        AuthenticationMiddleware = middleware_module.AuthenticationMiddleware
        SecurityHeadersMiddleware = middleware_module.SecurityHeadersMiddleware
        ErrorHandlingMiddleware = middleware_module.ErrorHandlingMiddleware

        __all__ = [
            "RateLimiter",
            "AuthenticationMiddleware",
            "SecurityHeadersMiddleware",
            "ErrorHandlingMiddleware",
        ]
    else:
        # Fallback if file doesn't exist
        __all__ = ["RateLimiter"]
except Exception as e:
    logger.warning("Could not load middleware classes: %s", e)
    __all__ = ["RateLimiter"]
