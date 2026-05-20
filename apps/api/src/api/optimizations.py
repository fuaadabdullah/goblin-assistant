"""
Performance optimizations for Goblin Assistant API
"""

import time
import asyncio
from typing import Dict, Any, Optional
from functools import wraps
import structlog
from fastapi import Request, Response
from starlette.responses import Response as StarletteResponse

# Configure logging
logger = structlog.get_logger()


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """Rate limiting decorator using in-memory storage for now.
    In production, this would use Redis or similar shared storage.
    """
    request_counts: Dict[str, Dict[str, int]] = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract client IP
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if request:
                client_ip = request.client.host if request.client else "unknown"
                current_time = int(time.time())
                window_start = (current_time // window_seconds) * window_seconds

                # Initialize if needed
                if client_ip not in request_counts:
                    request_counts[client_ip] = {}

                # Clean old windows
                for window in list(request_counts[client_ip].keys()):
                    if int(window) < window_start - window_seconds:
                        del request_counts[client_ip][window]

                # Check current window
                current_window = str(window_start)
                if current_window not in request_counts[client_ip]:
                    request_counts[client_ip][current_window] = 0

                request_counts[client_ip][current_window] += 1

                # Check if over limit
                if request_counts[client_ip][current_window] > max_requests:
                    logger.warning(
                        "rate_limit_exceeded",
                        client_ip=client_ip,
                        requests=request_counts[client_ip][current_window],
                        limit=max_requests,
                    )
                    return StarletteResponse(
                        content={"error": "Rate limit exceeded"},
                        status_code=429,
                        headers={"Retry-After": str(window_seconds)},
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def optimize_database_queries():
    """Decorator to optimize database queries with connection pooling insights"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Log slow queries
                if duration > 1.0:  # Log queries taking longer than 1 second
                    logger.warning(
                        "slow_database_query",
                        function=func.__name__,
                        duration=duration,
                    )

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "database_query_error",
                    function=func.__name__,
                    duration=duration,
                    error=str(e),
                )
                raise

        return wrapper

    return decorator


def cache_key_generator(request: Request) -> str:
    """Generate cache key from request"""
    # Include path and query parameters, exclude auth headers
    cache_key = f"{request.method}:{request.url.path}"

    # Add query parameters
    if request.url.query:
        cache_key += f"?{request.url.query}"

    # Add user agent for mobile/desktop optimization
    user_agent = request.headers.get("user-agent", "")
    if user_agent:
        cache_key += f":ua:{hash(user_agent)}"

    return cache_key


async def batch_process(items: list, batch_size: int = 10, delay: float = 0.1):
    """Process items in batches to avoid overwhelming external services"""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        # Process batch in parallel
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        results.extend(batch_results)

        # Add delay between batches to respect rate limits
        if i + batch_size < len(items):
            await asyncio.sleep(delay)

    return results
