"""
Secrets management router for FastAPI.

Provides HTTP endpoints for secrets operations using the universal secrets adapter.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from .integrations.secrets import (
    create_adapter,
    SecretAdapter,
    SecretAdapterError,
    SecretNotFoundError,
    SecretUnauthorizedError,
    SecretBackendError,
    SecretValidationError,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/secrets", tags=["secrets"])

# Global adapter instance
_secrets_adapter: Optional[SecretAdapter] = None


class SecretRequest(BaseModel):
    """Request model for creating/updating secrets."""

    path: str = Field(..., description="Secret path within the mount point")
    data: Dict[str, str] = Field(..., description="Secret data as key-value pairs")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional custom metadata"
    )
    version: Optional[int] = Field(
        None, description="Optional version for conditional updates"
    )


class SecretResponse(BaseModel):
    """Response model for secret operations."""

    path: str
    data: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = None
    backend_specific: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Response model for secrets health check."""

    status: str
    backend: str
    details: Dict[str, Any]
    timestamp: Optional[str] = None
    cache_stats: Optional[Dict[str, Any]] = None


def get_secrets_adapter() -> SecretAdapter:
    """Dependency to get the secrets adapter instance."""
    global _secrets_adapter
    if _secrets_adapter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Secrets adapter not initialized",
        )
    return _secrets_adapter


async def init_secrets_adapter() -> None:
    """Initialize the secrets adapter from environment variables."""
    global _secrets_adapter

    try:
        # Get configuration from environment
        secrets_backend = os.getenv("SECRETS_BACKEND", "vault").lower()
        vault_url = os.getenv("VAULT_URL", "http://localhost:8200")
        vault_mount_point = os.getenv("VAULT_MOUNT_POINT", "secret")
        vault_token = os.getenv("VAULT_TOKEN")
        vault_role_id = os.getenv("VAULT_ROLE_ID")
        vault_secret_id = os.getenv("VAULT_SECRET_ID")

        # Create adapter based on backend
        if secrets_backend == "vault":
            if vault_token:
                # Token-based authentication
                _secrets_adapter = create_adapter(
                    "vault",
                    vault_url=vault_url,
                    mount_point=vault_mount_point,
                )
                # Authenticate with token
                await _secrets_adapter.authenticate_with_token(vault_token)
                logger.info("Initialized Vault adapter with token authentication")

            elif vault_role_id and vault_secret_id:
                # AppRole authentication
                from .integrations.secrets.auth import AppRoleCredentials

                credentials = AppRoleCredentials(vault_role_id, vault_secret_id)
                _secrets_adapter = create_adapter(
                    "vault",
                    vault_url=vault_url,
                    mount_point=vault_mount_point,
                )
                
                # Authenticate with AppRole
                try:
                    token_credentials = await _secrets_adapter.authenticate_with_approle(
                        vault_role_id, vault_secret_id
                    )
                    credentials.set_session_token(token_credentials)
                    logger.info("Successfully initialized Vault adapter with AppRole authentication")
                except Exception as auth_error:
                    logger.error(f"AppRole authentication failed: {auth_error}")
                    raise ValueError(f"AppRole authentication failed: {auth_error}")

            else:
                raise ValueError(
                    "Either VAULT_TOKEN or (VAULT_ROLE_ID and VAULT_SECRET_ID) must be provided"
                )

        else:
            raise ValueError(f"Unsupported secrets backend: {secrets_backend}")

        logger.info(
            f"Successfully initialized secrets adapter for backend: {secrets_backend}"
        )

    except Exception as e:
        logger.error(f"Failed to initialize secrets adapter: {e}")
        raise


async def cleanup_secrets_adapter() -> None:
    """Clean up the secrets adapter instance."""
    global _secrets_adapter
    if _secrets_adapter is not None:
        await _secrets_adapter.close()
        _secrets_adapter = None
        logger.info("Cleaned up secrets adapter")


@router.get("/", response_model=Dict[str, str])
async def list_secrets(
    prefix: str = "",
    limit: int = 100,
    adapter: SecretAdapter = Depends(get_secrets_adapter),
):
    """
    List secrets under a given prefix.

    Args:
        prefix: Path prefix to filter secrets
        limit: Maximum number of secrets to return
        adapter: The secrets adapter instance

    Returns:
        List of secret paths
    """
    try:
        secret_paths = await adapter.list_secrets(prefix=prefix, limit=limit)
        return {"paths": secret_paths}

    except SecretUnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SecretBackendError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error listing secrets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/{path:path}", response_model=SecretResponse)
async def get_secret(
    path: str,
    version: Optional[int] = None,
    adapter: SecretAdapter = Depends(get_secrets_adapter),
):
    """
    Retrieve a secret by path.

    Args:
        path: Secret path
        version: Optional specific version
        adapter: The secrets adapter instance

    Returns:
        Secret data and metadata
    """
    try:
        secret = await adapter.get_secret(path, version)

        return SecretResponse(
            path=secret.path,
            data=secret.data,
            metadata={
                "created_at": secret.metadata.created_at.isoformat()
                if secret.metadata.created_at
                else None,
                "updated_at": secret.metadata.updated_at.isoformat()
                if secret.metadata.updated_at
                else None,
                "version": secret.metadata.version,
                "custom_metadata": secret.metadata.custom_metadata,
            },
            backend_specific=secret.metadata.backend_specific,
        )

    except SecretNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SecretUnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SecretBackendError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving secret {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/{path:path}", response_model=SecretResponse)
async def put_secret(
    path: str,
    request: SecretRequest,
    adapter: SecretAdapter = Depends(get_secrets_adapter),
):
    """
    Create or update a secret.

    Args:
        path: Secret path
        request: Secret data and metadata
        adapter: The secrets adapter instance

    Returns:
        Stored secret information
    """
    try:
        # Ensure path in request matches path parameter
        if request.path != path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path in request body must match URL path",
            )

        secret = await adapter.put_secret(
            path=path,
            data=request.data,
            metadata=request.metadata,
            version=request.version,
        )

        return SecretResponse(
            path=secret.path,
            data=secret.data,
            metadata={
                "created_at": secret.metadata.created_at.isoformat()
                if secret.metadata.created_at
                else None,
                "updated_at": secret.metadata.updated_at.isoformat()
                if secret.metadata.updated_at
                else None,
                "version": secret.metadata.version,
                "custom_metadata": secret.metadata.custom_metadata,
            },
            backend_specific=secret.metadata.backend_specific,
        )

    except SecretValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except SecretUnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SecretBackendError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error storing secret {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/{path:path}")
async def delete_secret(
    path: str,
    version: Optional[int] = None,
    adapter: SecretAdapter = Depends(get_secrets_adapter),
):
    """
    Delete a secret.

    Args:
        path: Secret path
        version: Optional specific version to delete
        adapter: The secrets adapter instance
    """
    try:
        await adapter.delete_secret(path, version)
        return {"message": f"Secret deleted: {path}"}

    except SecretNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SecretUnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SecretBackendError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting secret {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/{path:path}/rotate")
async def rotate_secret(
    path: str, adapter: SecretAdapter = Depends(get_secrets_adapter)
):
    """
    Rotate a secret value.

    Args:
        path: Secret path
        adapter: The secrets adapter instance

    Returns:
        New secret value
    """
    try:
        new_value = await adapter.rotate_secret(path)
        return {"path": path, "new_value": new_value}

    except SecretNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SecretUnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SecretBackendError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error rotating secret {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/health", response_model=HealthResponse)
async def secrets_health(adapter: SecretAdapter = Depends(get_secrets_adapter)):
    """
    Check the health of the secrets adapter.

    Args:
        adapter: The secrets adapter instance

    Returns:
        Health status and details
    """
    try:
        health_data = await adapter.health()

        # Get backend type dynamically
        backend = "unknown"
        if hasattr(adapter, "__class__"):
            class_name = adapter.__class__.__name__.lower()
            if "vault" in class_name:
                backend = "vault"
            elif "bitwarden" in class_name:
                backend = "bitwarden"

        # Get cache stats if available
        cache_stats = None
        if hasattr(adapter, "cache") and hasattr(adapter.cache, "stats"):
            cache_stats = await adapter.cache.stats()

        return HealthResponse(
            status=health_data.get("status", "unknown"),
            backend=backend,
            details=health_data,
            timestamp=health_data.get("timestamp"),
            cache_stats=cache_stats,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            backend="unknown",
            details={"error": str(e)},
        )
