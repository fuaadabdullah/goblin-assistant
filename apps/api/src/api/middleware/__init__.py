"""Middleware package for Goblin Assistant API."""

from .rate_limiter import RateLimiter

# Import middleware classes from the api/middleware.py file (sibling to this package)
# We need to use importlib because Python prioritizes the package over the .py file
try:
    import importlib.util
    import sys
    from pathlib import Path

    # Get path to middleware.py file (sibling to middleware/ directory)
    middleware_py_path = Path(__file__).parent.parent / "middleware.py"

    if middleware_py_path.exists():
        # Load the module from the file
        spec = importlib.util.spec_from_file_location(
            "api_middleware_file", middleware_py_path
        )
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
    # If anything goes wrong, just export RateLimiter
    import sys

    print(f"Warning: Could not load middleware classes: {e}", file=sys.stderr)
    __all__ = ["RateLimiter"]
