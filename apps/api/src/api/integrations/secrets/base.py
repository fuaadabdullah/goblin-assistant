"""
Base adapter interface and common types for secrets management.

This module defines the abstract interface that all secrets adapters must implement,
along with common error types and data structures.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio


class SecretAdapterError(Exception):
    """Base exception for all secrets adapter errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code or "UNKNOWN_ERROR"
        self.details = details or {}


class SecretNotFoundError(SecretAdapterError):
    """Raised when a requested secret cannot be found."""

    def __init__(self, path: str):
        super().__init__(
            f"Secret not found at path: {path}", "NOT_FOUND", {"path": path}
        )


class SecretUnauthorizedError(SecretAdapterError):
    """Raised when authentication/authorization fails."""

    def __init__(self, message: str = "Unauthorized access to secrets"):
        super().__init__(message, "UNAUTHORIZED")


class SecretBackendError(SecretAdapterError):
    """Raised when the backend service is unavailable or returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, "BACKEND_ERROR", {"status_code": status_code})


class SecretValidationError(SecretAdapterError):
    """Raised when secret data fails validation."""

    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        super().__init__(
            message, "VALIDATION_ERROR", {"validation_errors": validation_errors or []}
        )


class SecretMetadata:
    """Metadata associated with a secret."""

    def __init__(
        self,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        version: Optional[int] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
        backend_specific: Optional[Dict[str, Any]] = None,
    ):
        self.created_at = created_at
        self.updated_at = updated_at
        self.version = version
        self.custom_metadata = custom_metadata or {}
        self.backend_specific = backend_specific or {}


class Secret:
    """Represents a secret with its data and metadata."""

    def __init__(
        self,
        path: str,
        data: Dict[str, str],
        metadata: Optional[SecretMetadata] = None,
    ):
        self.path = path
        self.data = data
        self.metadata = metadata or SecretMetadata()

    def get_secret_value(self, key: str = "value") -> Optional[str]:
        """Get a secret value by key, with 'value' as default."""
        return self.data.get(key)

    def to_dict(self) -> Dict[str, Any]:
        """Convert secret to dictionary representation."""
        return {
            "path": self.path,
            "data": self.data,
            "metadata": {
                "created_at": self.metadata.created_at.isoformat()
                if self.metadata.created_at
                else None,
                "updated_at": self.metadata.updated_at.isoformat()
                if self.metadata.updated_at
                else None,
                "version": self.metadata.version,
                "custom_metadata": self.metadata.custom_metadata,
                "backend_specific": self.metadata.backend_specific,
            },
        }


class SecretAdapter(ABC):
    """
    Abstract base class for all secrets adapters.

    Implementations must provide async methods for secrets operations.
    All adapters should handle authentication, caching, retries, and error handling.
    """

    @abstractmethod
    async def get_secret(self, path: str, version: Optional[int] = None) -> Secret:
        """
        Retrieve a secret by path.

        Args:
            path: The path/identifier for the secret
            version: Optional specific version to retrieve (for versioned backends)

        Returns:
            Secret object containing the secret data and metadata

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretUnauthorizedError: If authentication fails
            SecretBackendError: If the backend service is unavailable
        """
        pass

    @abstractmethod
    async def put_secret(
        self,
        path: str,
        data: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        version: Optional[int] = None,
    ) -> Secret:
        """
        Create or update a secret.

        Args:
            path: The path/identifier for the secret
            data: The secret data as key-value pairs
            metadata: Optional custom metadata
            version: Optional version for update operations

        Returns:
            Secret object representing the stored secret

        Raises:
            SecretValidationError: If the data fails validation
            SecretUnauthorizedError: If write permissions are denied
            SecretBackendError: If the backend service is unavailable
        """
        pass

    @abstractmethod
    async def list_secrets(self, prefix: str = "", limit: int = 100) -> List[str]:
        """
        List secret paths under a given prefix.

        Args:
            prefix: The path prefix to filter secrets
            limit: Maximum number of secrets to return

        Returns:
            List of secret paths that match the prefix

        Raises:
            SecretUnauthorizedError: If list permissions are denied
            SecretBackendError: If the backend service is unavailable
        """
        pass

    @abstractmethod
    async def delete_secret(self, path: str, version: Optional[int] = None) -> None:
        """
        Delete a secret.

        Args:
            path: The path/identifier for the secret
            version: Optional specific version to delete

        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretUnauthorizedError: If delete permissions are denied
            SecretBackendError: If the backend service is unavailable
        """
        pass

    async def rotate_secret(self, path: str) -> str:
        """
        Rotate/regenerate a secret value.

        Note: Not all backends support automatic rotation. Implementations
        should raise NotImplementedError if rotation is not supported.

        Args:
            path: The path/identifier for the secret

        Returns:
            The new secret value or rotation workflow ID

        Raises:
            NotImplementedError: If rotation is not supported
            Other SecretAdapterError subclasses: For rotation failures
        """
        raise NotImplementedError(
            f"Secret rotation not supported by {self.__class__.__name__}"
        )

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """
        Check the health of the adapter and backend.

        Returns:
            Dictionary containing health status and metadata
                - status: "healthy", "degraded", or "unhealthy"
                - response_time: Optional response time in seconds
                - backend_version: Optional backend version info
                - kv_version: Optional KV version (for KV backends)
                - other relevant metadata

        Raises:
            SecretBackendError: If health check itself fails
        """
        pass

    async def close(self) -> None:
        """
        Close any resources held by the adapter.

        Called when the adapter is no longer needed.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.create_task(self.close())
