"""
Enhanced Security Middleware for Operational Endpoints
Implements read-only by default with environment-based access control
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

from ..security_config import SecurityConfig
from ..storage.cache import cache

logger = logging.getLogger(__name__)


class OpsSecurityConfig:
    """Security configuration for operational endpoints"""

    # Environment-based access control
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    OPS_READ_ONLY = os.getenv("OPS_READ_ONLY", "true").lower() == "true"
    OPS_ALLOWED_ENVIRONMENTS = os.getenv(
        "OPS_ALLOWED_ENVIRONMENTS", "development,staging"
    ).split(",")

    # Authentication requirements
    REQUIRE_AUTH = os.getenv("OPS_REQUIRE_AUTH", "true").lower() == "true"
    JWT_SECRET = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = int(os.getenv("OPS_JWT_EXPIRATION_HOURS", "24"))

    # Rate limiting for ops endpoints
    RATE_LIMIT_ENABLED = os.getenv("OPS_RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS = int(os.getenv("OPS_RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("OPS_RATE_LIMIT_WINDOW", "3600"))  # 1 hour

    # Audit logging
    AUDIT_LOGGING_ENABLED = os.getenv("OPS_AUDIT_LOGGING", "true").lower() == "true"
    AUDIT_LOG_KEY = "ops_audit_log"

    # Allowed operations per environment
    ENVIRONMENT_PERMISSIONS = {
        "development": ["read", "write", "reset", "debug"],
        "staging": ["read", "write", "reset"],
        "production": ["read"],  # Production is read-only by default
    }


class OpsSecurityMiddleware:
    """Security middleware for operational endpoints with environment-based access control"""

    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
        self.rate_limit_cache = {}

    async def check_environment_access(self, operation: str = "read") -> bool:
        """Check if current environment allows the requested operation"""
        current_env = OpsSecurityConfig.ENVIRONMENT

        # Check if environment is allowed for ops access
        if current_env not in OpsSecurityConfig.OPS_ALLOWED_ENVIRONMENTS:
            logger.warning(f"Environment {current_env} not allowed for ops access")
            return False

        # Check if operation is allowed in current environment
        allowed_operations = OpsSecurityConfig.ENVIRONMENT_PERMISSIONS.get(
            current_env, []
        )
        if operation not in allowed_operations:
            logger.warning(
                f"Operation {operation} not allowed in environment {current_env}"
            )
            return False

        return True

    async def authenticate_request(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
    ) -> Dict[str, Any]:
        """Authenticate request for ops endpoints"""
        if not OpsSecurityConfig.REQUIRE_AUTH:
            return {
                "user": "anonymous",
                "authenticated": False,
                "permissions": ["read"],
            }

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for ops endpoints",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # Decode JWT token
            payload = jwt.decode(
                credentials.credentials,
                OpsSecurityConfig.JWT_SECRET,
                algorithms=[OpsSecurityConfig.JWT_ALGORITHM],
            )

            # Check if user has ops permissions
            user_permissions = payload.get("permissions", [])
            if "ops" not in user_permissions and "admin" not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions for ops endpoints",
                )

            return {
                "user": payload.get("user_id"),
                "authenticated": True,
                "permissions": user_permissions,
                "exp": payload.get("exp"),
            }

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def check_rate_limit(self, client_id: str) -> bool:
        """Check rate limiting for ops endpoints"""
        if not OpsSecurityConfig.RATE_LIMIT_ENABLED:
            return True

        current_time = time.time()
        window_start = current_time - OpsSecurityConfig.RATE_LIMIT_WINDOW

        # Clean old entries
        if client_id in self.rate_limit_cache:
            self.rate_limit_cache[client_id] = [
                req_time
                for req_time in self.rate_limit_cache[client_id]
                if req_time > window_start
            ]
        else:
            self.rate_limit_cache[client_id] = []

        # Check if under limit
        if (
            len(self.rate_limit_cache[client_id])
            >= OpsSecurityConfig.RATE_LIMIT_REQUESTS
        ):
            return False

        # Record this request
        self.rate_limit_cache[client_id].append(current_time)
        return True

    async def log_audit_event(
        self,
        request: Request,
        user: str,
        operation: str,
        resource: str,
        success: bool,
        details: Dict[str, Any] = None,
    ):
        """Log audit event for ops operations"""
        if not OpsSecurityConfig.AUDIT_LOGGING_ENABLED:
            return

        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": user,
            "operation": operation,
            "resource": resource,
            "success": success,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "environment": OpsSecurityConfig.ENVIRONMENT,
            "details": details or {},
        }

        # Log to console
        logger.info(f"OPS AUDIT: {audit_event}")

        # Store in cache for retrieval
        try:
            audit_log = await cache.get(OpsSecurityConfig.AUDIT_LOG_KEY) or []
            audit_log.append(audit_event)

            # Keep only last 1000 entries
            if len(audit_log) > 1000:
                audit_log = audit_log[-1000:]

            await cache.set(
                OpsSecurityConfig.AUDIT_LOG_KEY, audit_log, expire=86400 * 7
            )  # 7 days
        except Exception as e:
            logger.error(f"Failed to store audit log: {e}")


# Global security instance
ops_security = OpsSecurityMiddleware()


def require_ops_access(operation: str = "read"):
    """Decorator to require ops access with environment and authentication checks"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs or args
            request = None
            credentials = None

            # Try to get request from kwargs
            if "request" in kwargs:
                request = kwargs["request"]
            else:
                # Try to find request in args (usually first argument for FastAPI endpoints)
                for arg in args:
                    if hasattr(arg, "client") and hasattr(arg, "headers"):
                        request = arg
                        break

            # Get credentials from request
            if request:
                try:
                    from fastapi.security import HTTPBearer

                    security = HTTPBearer(auto_error=False)
                    credentials = await security.__call__(request)
                except:
                    pass

            # Check environment access
            env_allowed = await ops_security.check_environment_access(operation)
            if not env_allowed:
                await ops_security.log_audit_event(
                    request,
                    "system",
                    operation,
                    "ops_endpoint",
                    False,
                    {
                        "reason": "environment_not_allowed",
                        "environment": OpsSecurityConfig.ENVIRONMENT,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Ops operations not allowed in {OpsSecurityConfig.ENVIRONMENT} environment",
                )

            # Authenticate request
            auth_result = await ops_security.authenticate_request(request, credentials)

            # Check rate limiting
            client_id = auth_result.get("user", "anonymous")
            if not await ops_security.check_rate_limit(client_id):
                await ops_security.log_audit_event(
                    request,
                    client_id,
                    operation,
                    "ops_endpoint",
                    False,
                    {"reason": "rate_limit_exceeded"},
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded for ops endpoints",
                )

            # Log successful access
            await ops_security.log_audit_event(
                request,
                client_id,
                operation,
                "ops_endpoint",
                True,
                {
                    "auth_method": "jwt"
                    if auth_result.get("authenticated")
                    else "anonymous"
                },
            )

            # Call the original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_ops_write_access():
    """Decorator for write operations on ops endpoints"""
    return require_ops_access("write")


def require_ops_reset_access():
    """Decorator for circuit breaker reset operations"""
    return require_ops_access("reset")


def require_ops_debug_access():
    """Decorator for debug operations"""
    return require_ops_access("debug")


async def get_ops_audit_log(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get audit log for ops operations"""
    try:
        audit_log = await cache.get(OpsSecurityConfig.AUDIT_LOG_KEY) or []

        # Sort by timestamp (newest first)
        audit_log.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply pagination
        start = offset
        end = offset + limit
        return audit_log[start:end]

    except Exception as e:
        logger.error(f"Failed to retrieve audit log: {e}")
        return []


async def check_ops_permissions(user_permissions: List[str], operation: str) -> bool:
    """Check if user has permissions for the operation"""
    if "admin" in user_permissions:
        return True

    if operation == "read" and "ops_read" in user_permissions:
        return True

    if operation in ["write", "reset"] and "ops_write" in user_permissions:
        return True

    if operation == "debug" and "ops_debug" in user_permissions:
        return True

    return False


def get_security_summary() -> Dict[str, Any]:
    """Get security configuration summary"""
    return {
        "environment": OpsSecurityConfig.ENVIRONMENT,
        "read_only_mode": OpsSecurityConfig.OPS_READ_ONLY,
        "auth_required": OpsSecurityConfig.REQUIRE_AUTH,
        "rate_limiting_enabled": OpsSecurityConfig.RATE_LIMIT_ENABLED,
        "audit_logging_enabled": OpsSecurityConfig.AUDIT_LOGGING_ENABLED,
        "allowed_environments": OpsSecurityConfig.OPS_ALLOWED_ENVIRONMENTS,
        "permissions": OpsSecurityConfig.ENVIRONMENT_PERMISSIONS.get(
            OpsSecurityConfig.ENVIRONMENT, []
        ),
        "security_warnings": validate_ops_security(),
    }


def validate_ops_security() -> List[str]:
    """Validate ops security configuration and return warnings"""
    warnings = []

    # Check environment configuration
    if OpsSecurityConfig.ENVIRONMENT not in OpsSecurityConfig.OPS_ALLOWED_ENVIRONMENTS:
        warnings.append(
            f"Environment {OpsSecurityConfig.ENVIRONMENT} not in allowed environments"
        )

    # Check JWT secret in production
    if OpsSecurityConfig.ENVIRONMENT == "production":
        if OpsSecurityConfig.JWT_SECRET == "fallback-secret-key-change-in-production":
            warnings.append("CRITICAL: Using default JWT secret in production!")

        if not OpsSecurityConfig.REQUIRE_AUTH:
            warnings.append("CRITICAL: Authentication disabled in production!")

    # Check rate limiting
    if not OpsSecurityConfig.RATE_LIMIT_ENABLED:
        warnings.append("WARNING: Rate limiting disabled for ops endpoints")

    # Check audit logging
    if not OpsSecurityConfig.AUDIT_LOGGING_ENABLED:
        warnings.append("WARNING: Audit logging disabled for ops operations")

    return warnings


# Initialize security validation on import
security_warnings = validate_ops_security()
if security_warnings:
    logger.warning("OPS SECURITY WARNINGS:")
    for warning in security_warnings:
        logger.warning(f"  - {warning}")
else:
    logger.info("Ops security configuration validated successfully")
