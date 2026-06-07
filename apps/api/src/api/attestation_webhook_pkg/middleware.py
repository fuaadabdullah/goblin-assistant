"""Authentication and rate-limiting middleware for the attestation webhook."""

import logging
import os
import time
from functools import wraps
from typing import Any, Awaitable, Callable, Optional

from fastapi import HTTPException, Request

from .auth import get_verified_identity, verify_service_account_token

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("attestation.webhook.audit")


def rate_limit(
    limit_per_min: Optional[int] = None,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Simple Redis-backed fixed-window rate limiter decorator.

    Key is based on ServiceAccount username when available,
    otherwise remote IP.
    """

    def decorator(
        func: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            sa = get_verified_identity(request)
            remote = None
            try:
                remote = request.client.host if request.client else None
            except AttributeError:
                remote = request.headers.get("X-Forwarded-For") or "unknown"

            key_id = sa or remote or "unknown"
            if limit_per_min is None:
                limit = int(os.getenv("ATTEST_NODE_RATE_LIMIT_PER_MIN", "60"))
            else:
                limit = int(limit_per_min)

            try:
                import redis as _redis

                from ..attestation_service import get_attestation_service

                redis_client = get_attestation_service().redis_client
                now = int(time.time())
                window = now // 60
                key = f"attestation:ratelimit:{key_id}:{window}"
                try:
                    count = redis_client.incr(key)
                    if count == 1:
                        redis_client.expire(key, 60)
                    if count > limit:
                        extra = {"key": key_id, "count": count}
                        audit_logger.warning("rate_limit_exceeded", extra=extra)
                        raise HTTPException(
                            status_code=429,
                            detail="Rate limit exceeded",
                        )
                except _redis.RedisError as exc:
                    logger.exception("rate_limit_redis_error", exc_info=exc)
            except (ImportError, AttributeError) as exc:
                logger.debug("rate_limit_unavailable", exc_info=exc)

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_mtls(func):
    """Decorator to require mTLS (or proxy-forwarded client cert) for requests.

    Requires X-SSL-Client-Verify: SUCCESS from the TLS-terminating reverse
    proxy. When ATTEST_TRUSTED_CLIENT_DN is configured the client DN must also
    match exactly, preventing spoofed-header bypass by an attacker who knows
    the expected verify value but not the DN.

    Use SKIP_MTLS_CHECK=true in env for local development/testing only.
    """

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if os.getenv("SKIP_MTLS_CHECK", "false").lower() == "true":
            return await func(request, *args, **kwargs)

        verify_header = request.headers.get("X-SSL-Client-Verify") or request.headers.get(
            "X-Client-Verify"
        )
        client_dn = request.headers.get("X-SSL-Client-S-DN") or request.headers.get(
            "X-SSL-CLIENT-S-DN"
        )
        trusted_dn = os.getenv("ATTEST_TRUSTED_CLIENT_DN", "").strip()

        verified = bool(verify_header and verify_header.upper() == "SUCCESS")
        # When a trusted DN is configured the presented DN must match exactly.
        dn_ok = (not trusted_dn) or (client_dn == trusted_dn)

        if verified and dn_ok:
            return await func(request, *args, **kwargs)

        audit_logger.warning(
            "mtls_rejected",
            extra={
                "path": request.url.path,
                "verify_header_present": bool(verify_header),
                "verified": verified,
                "dn_match": dn_ok,
            },
        )
        raise HTTPException(status_code=403, detail="mTLS required")

    return wrapper


def require_bearer_token(func):
    """Decorator to require Bearer token authentication.

    SECURITY: Validates Authorization header contains Bearer token.
    Returns 401 if missing or invalid.
    """

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        path = request.url.path

        if not auth_header.startswith("Bearer "):
            audit_logger.warning("attest_node_missing_auth", extra={"path": path})
            raise HTTPException(status_code=401, detail="Authorization header required")

        token = auth_header[7:]
        if not token:
            audit_logger.warning("attest_node_empty_token", extra={"path": path})
            raise HTTPException(status_code=401, detail="Authorization token required")

        sa_username = verify_service_account_token(token)
        if not sa_username:
            audit_logger.warning("attest_node_invalid_token", extra={"path": path})
            raise HTTPException(status_code=401, detail="Invalid service account token")

        request.state.service_account_username = sa_username
        return await func(request, *args, **kwargs)

    return wrapper
