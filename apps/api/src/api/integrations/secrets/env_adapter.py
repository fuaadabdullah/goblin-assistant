"""
Environment variable adapter for secrets management.

Provides a SecretAdapter implementation that reads secrets directly from
os.environ. This is the default adapter when no external vault (Vault,
Bitwarden) has been configured, so the application boots without requiring
VAULT_TOKEN or VAULT_ROLE_ID+VAULT_SECRET_ID.

Write operations (put_secret, delete_secret, rotate_secret) are not
supported at runtime since environment variables are process-immutable.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import (
    SecretAdapter,
    Secret,
    SecretMetadata,
    SecretNotFoundError,
    SecretBackendError,
)

logger = logging.getLogger(__name__)


class EnvAdapter(SecretAdapter):
    """
    Secrets adapter backed by process environment variables.

    This adapter allows the secrets infrastructure to function without
    an external vault.  Secrets are read from ``os.environ`` at call time,
    so they reflect whatever the process was started with (.env files,
    Docker env, platform secrets, etc.).

    Because environment variables cannot be mutated at runtime after
    the process starts, write operations raise ``SecretBackendError``.
    """

    def __init__(self, prefix: str = "", cache_ttl: int = 300, cache_size: int = 1000):
        """
        Initialize environment-variable adapter.

        Args:
            prefix: Optional prefix stripped from secret paths when
                    looking up environment variable names.
            cache_ttl: Ignored – env vars are not cached (already in-memory).
            cache_size: Ignored – env vars are not cached.
        """
        self._prefix = prefix
        # Disable caching – os.environ lookups are already O(1) in-memory.
        self.cache = None  # type: ignore[assignment]
        logger.debug("EnvAdapter initialized with prefix=%r", prefix)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _resolve_key(self, path: str) -> str:
        """Convert a secret path to an environment variable name."""
        key = path.lstrip("/")
        if self._prefix and not key.startswith(self._prefix):
            key = f"{self._prefix}{key}"
        return key

    # ------------------------------------------------------------------
    # SecretAdapter interface
    # ------------------------------------------------------------------

    async def get_secret(self, path: str, version: Optional[int] = None) -> Secret:
        """
        Retrieve a secret from the process environment.

        Args:
            path: Environment variable name to read.
            version: Ignored – env vars are not versioned.

        Returns:
            Secret object with the env var value.

        Raises:
            SecretNotFoundError: If the environment variable is not set.
        """
        key = self._resolve_key(path)
        value = os.getenv(key)
        if value is None:
            raise SecretNotFoundError(path)

        now = datetime.utcnow()
        metadata = SecretMetadata(
            created_at=now,
            updated_at=now,
            version=1,
            custom_metadata={"source": "environment_variable"},
            backend_specific={
                "resolved_key": key,
                "is_set": key in os.environ,
            },
        )
        logger.debug("EnvAdapter: resolved %s -> %s (set=%s)", path, key, key in os.environ)
        return Secret(path, {"value": value}, metadata)

    async def put_secret(
        self,
        path: str,
        data: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        version: Optional[int] = None,
    ) -> Secret:
        """
        Writing secrets at runtime is not supported for env vars.

        Raises:
            SecretBackendError: Always – environment variables are
                                process-immutable.
        """
        raise SecretBackendError(
            "Cannot write secrets to environment variables at runtime. "
            "Set the variable before starting the process or switch to "
            "a writable backend (vault / bitwarden)."
        )

    async def list_secrets(self, prefix: str = "", limit: int = 100) -> List[str]:
        """
        List environment variable names that match *prefix*.

        Args:
            prefix: Filter by variable name (case-sensitive).
            limit: Maximum number of names to return.

        Returns:
            Sorted list of matching variable names (up to *limit*).
        """
        resolved_prefix = self._resolve_key(prefix)
        matching = [k for k in os.environ if k.startswith(resolved_prefix)]
        matching.sort()
        return matching[:limit]

    async def delete_secret(self, path: str, version: Optional[int] = None) -> None:
        """
        Deleting environment variables at runtime is not supported.

        Raises:
            SecretBackendError: Always – env vars are process-immutable.
        """
        raise SecretBackendError(
            "Cannot delete environment variables at runtime. "
            "Unset the variable before starting the process or switch to "
            "a writable backend (vault / bitwarden)."
        )

    async def rotate_secret(self, path: str) -> str:
        """
        Rotation is not supported for environment variables.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "Secret rotation is not supported by EnvAdapter. "
            "Set a new value in your environment / .env file and restart "
            "the process, or switch to a writable backend (vault / bitwarden)."
        )

    async def health(self) -> Dict[str, Any]:
        """
        Health check – always healthy when the adapter is loaded.

        Returns:
            Dictionary with status and metadata.
        """
        return {
            "status": "healthy",
            "backend": "env",
            "authenticated": True,
            "prefix": self._prefix,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def close(self) -> None:
        """Nothing to clean up – env vars are process-scoped."""
        pass
