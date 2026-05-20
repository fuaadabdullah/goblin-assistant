"""
HashiCorp Vault adapter for secrets management.

Provides async interface to HashiCorp Vault KV v1 and v2 engines.
Supports multiple authentication methods including token and AppRole.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import aiohttp
import hvac
from hvac.exceptions import InvalidPath, VaultError, Forbidden

from .base import (
    SecretAdapter,
    Secret,
    SecretMetadata,
    SecretAdapterError,
    SecretNotFoundError,
    SecretUnauthorizedError,
    SecretBackendError,
    SecretValidationError,
)
from .cache import SecretCache
from .auth import TokenCredentials, AppRoleCredentials, get_auth_manager

logger = logging.getLogger(__name__)


def _parse_vault_time(time_str: Optional[str]) -> Optional[datetime]:
    """Parse Vault timestamp string to datetime object."""
    if not time_str:
        return None
    try:
        # Vault returns ISO 8601 format
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except Exception:
        return None


class VaultAdapter(SecretAdapter):
    """
    HashiCorp Vault adapter for secrets operations.

    Supports KV v1 and v2 secret engines, with automatic version detection.
    """

    def __init__(
        self,
        vault_url: str,
        mount_point: str = "secret",
        verify_ssl: bool = True,
        timeout: int = 30,
        cache_ttl: int = 300,
        cache_size: int = 1000,
    ):
        """
        Initialize Vault adapter.

        Args:
            vault_url: Vault server URL (e.g., http://localhost:8200)
            mount_point: KV engine mount point (default: secret)
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
            cache_ttl: Cache time-to-live in seconds
            cache_size: Maximum cache entries
        """
        self.vault_url = vault_url.rstrip("/")
        self.mount_point = mount_point
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._client: Optional[hvac.Client] = None
        self._kv_version: Optional[int] = None

        # Initialize cache
        self.cache = SecretCache(max_size=cache_size, default_ttl=cache_ttl)

        # Auth manager
        self.auth_manager = get_auth_manager()

        # Connection pool
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(
                    verify_ssl=self.verify_ssl,
                    limit=100,  # Connection pool limit
                    limit_per_host=30,  # Per-host limit
                ),
            )
        return self._session

    async def _get_client(self) -> hvac.Client:
        """Get or create Vault client."""
        if self._client is None:
            self._client = hvac.Client(
                url=self.vault_url,
                verify=self.verify_ssl,
                session=self._get_session(),
            )
        return self._client

    async def authenticate_with_token(self, token: str) -> bool:
        """
        Authenticate Vault client with token.

        Args:
            token: Vault token

        Returns:
            True if authentication successful

        Raises:
            SecretUnauthorizedError: If authentication fails
        """
        try:
            client = await self._get_client()
            client.token = token

            # Verify the token is valid
            if client.is_authenticated():
                logger.info("Successfully authenticated to Vault with token")
                return True
            else:
                raise SecretUnauthorizedError("Token authentication failed")
        except Exception as e:
            logger.error(f"Vault token authentication error: {e}")
            raise SecretUnauthorizedError(f"Token authentication failed: {e}")

    async def authenticate_with_approle(
        self, role_id: str, secret_id: str
    ) -> TokenCredentials:
        """
        Authenticate Vault client with AppRole.

        Args:
            role_id: AppRole role ID
            secret_id: AppRole secret ID

        Returns:
            TokenCredentials with the authenticated token

        Raises:
            SecretUnauthorizedError: If authentication fails
        """
        try:
            client = await self._get_client()

            # Perform AppRole login
            response = client.auth.approle.login(
                role_id=role_id,
                secret_id=secret_id,
            )

            # Extract token from response
            token = response["auth"]["client_token"]
            lease_duration = response["auth"].get("lease_duration", 0)

            # Set the token on the client
            client.token = token

            # Verify authentication
            if not client.is_authenticated():
                raise SecretUnauthorizedError("AppRole authentication failed")

            logger.info("Successfully authenticated to Vault with AppRole")

            # Create TokenCredentials with expiry
            expires_at = None
            if lease_duration > 0:
                from datetime import timedelta
                expires_at = datetime.utcnow() + timedelta(seconds=lease_duration)

            return TokenCredentials(token=token, expires_at=expires_at)

        except Exception as e:
            logger.error(f"Vault AppRole authentication error: {e}")
            raise SecretUnauthorizedError(f"AppRole authentication failed: {e}")

    async def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated."""
        client = await self._get_client()
        if not client.is_authenticated():
            raise SecretUnauthorizedError("Vault client is not authenticated")

    async def _detect_kv_version(self) -> int:
        """
        Detect KV engine version (1 or 2).

        Returns:
            KV version number

        Raises:
            SecretBackendError: If unable to detect version
        """
        if self._kv_version is not None:
            return self._kv_version

        try:
            client = await self._get_client()

            # Try to get mount configuration
            mounts = client.sys.list_mounted_secrets_engines()

            if self.mount_point in mounts:
                mount_config = mounts[self.mount_point]
                options = mount_config.get("options", {})

                # KV v2 has "version" option
                if "version" in options:
                    version = options["version"]
                    if version in ["1", "2"]:
                        self._kv_version = int(version)
                        logger.info(
                            f"Detected Vault KV v{self._kv_version} at mount {self.mount_point}"
                        )
                        return self._kv_version

            # Default to v1 if we can't determine
            self._kv_version = 1
            logger.warning(
                f"Could not detect KV version for mount {self.mount_point}, defaulting to v1"
            )
            return self._kv_version

        except Exception as e:
            logger.error(f"Failed to detect KV version: {e}")
            raise SecretBackendError(f"Unable to detect Vault KV version: {e}")

    async def get_secret(self, path: str, version: Optional[int] = None) -> Secret:
        """
        Retrieve secret from Vault.

        Args:
            path: Secret path within the mount point
            version: Optional specific version (KV v2 only)

        Returns:
            Secret object

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretUnauthorizedError: If authentication fails
            SecretBackendError: If Vault is unavailable
        """
        try:
            await self._ensure_authenticated()
            kv_version = await self._detect_kv_version()

            # Check cache first
            cached_secret = await self.cache.get_secret(path, version)
            if cached_secret is not None:
                logger.debug(f"Cache hit for secret: {path}")
                return Secret(
                    path,
                    cached_secret["data"],
                    SecretMetadata(**cached_secret["metadata"]),
                )

            client = await self._get_client()
            full_path = f"{self.mount_point}/{path.lstrip('/')}"

            # Handle KV v1 vs v2
            if kv_version == 2:
                if version is not None:
                    # Get specific version
                    response = client.secrets.kv.v2.read_secret_version(
                        path=path,
                        version=version,
                        mount_point=self.mount_point,
                    )
                else:
                    # Get latest version
                    response = client.secrets.kv.v2.read_secret_version(
                        path=path,
                        mount_point=self.mount_point,
                    )

                # Extract data and metadata
                secret_data = response["data"]["data"]
                metadata = response["data"]["metadata"]

                # Create metadata object
                secret_metadata = SecretMetadata(
                    created_at=_parse_vault_time(metadata.get("created_time")),
                    updated_at=_parse_vault_time(metadata.get("updated_time")),
                    version=metadata.get("version"),
                    custom_metadata=metadata.get("custom_metadata", {}),
                    backend_specific={
                        "vault_kv_version": 2,
                        "mount_point": self.mount_point,
                        "cas_version": metadata.get("cas_version"),
                    },
                )

            else:  # KV v1
                response = client.secrets.kv.v1.read_secret(
                    path=path,
                    mount_point=self.mount_point,
                )

                secret_data = response["data"]

                # KV v1 has limited metadata
                secret_metadata = SecretMetadata(
                    created_at=None,
                    updated_at=None,
                    version=None,
                    custom_metadata={},
                    backend_specific={
                        "vault_kv_version": 1,
                        "mount_point": self.mount_point,
                    },
                )

            # Create Secret object
            secret = Secret(path, secret_data, secret_metadata)

            # Cache the result
            await self.cache.set_secret(
                path,
                {
                    "data": secret_data,
                    "metadata": {
                        "created_at": secret_metadata.created_at,
                        "updated_at": secret_metadata.updated_at,
                        "version": secret_metadata.version,
                        "custom_metadata": secret_metadata.custom_metadata,
                        "backend_specific": secret_metadata.backend_specific,
                    },
                },
                version,
            )

            logger.info(f"Retrieved secret from Vault: {path}")
            return secret

        except InvalidPath:
            raise SecretNotFoundError(f"Secret not found at path: {path}")
        except Forbidden:
            raise SecretUnauthorizedError(f"Access denied to secret: {path}")
        except VaultError as e:
            raise SecretBackendError(f"Vault error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret {path}: {e}")
            raise SecretBackendError(f"Failed to retrieve secret: {e}")

    async def put_secret(
        self,
        path: str,
        data: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        version: Optional[int] = None,
    ) -> Secret:
        """
        Store secret in Vault.

        Args:
            path: Secret path within the mount point
            data: Secret data as key-value pairs
            metadata: Optional custom metadata (KV v2 only)
            version: Optional version for conditional updates (KV v2 only)

        Returns:
            Secret object representing the stored secret

        Raises:
            SecretValidationError: If data validation fails
            SecretUnauthorizedError: If write permissions are denied
            SecretBackendError: If Vault is unavailable
        """
        try:
            await self._ensure_authenticated()
            kv_version = await self._detect_kv_version()

            # Validate data
            if not data:
                raise SecretValidationError("Secret data cannot be empty")

            if not isinstance(data, dict):
                raise SecretValidationError("Secret data must be a dictionary")

            client = await self._get_client()
            full_path = f"{self.mount_point}/{path.lstrip('/')}"

            # Handle KV v1 vs v2
            if kv_version == 2:
                # Prepare parameters
                write_params = {"data": data}

                if metadata:
                    write_params["options"] = (
                        {"cas": version} if version is not None else {}
                    )
                    write_params["metadata"] = metadata
                elif version is not None:
                    write_params["options"] = {"cas": version}

                response = client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret=write_params,
                    mount_point=self.mount_point,
                )

                # Extract response data
                metadata_response = response["data"]["metadata"]

                secret_metadata = SecretMetadata(
                    created_at=_parse_vault_time(metadata_response.get("created_time")),
                    updated_at=_parse_vault_time(metadata_response.get("updated_time")),
                    version=metadata_response.get("version"),
                    custom_metadata=metadata_response.get("custom_metadata", {}),
                    backend_specific={
                        "vault_kv_version": 2,
                        "mount_point": self.mount_point,
                        "cas_version": metadata_response.get("cas_version"),
                    },
                )

            else:  # KV v1
                client.secrets.kv.v1.create_or_update_secret(
                    path=path,
                    secret=data,
                    mount_point=self.mount_point,
                )

                secret_metadata = SecretMetadata(
                    created_at=None,
                    updated_at=None,
                    version=None,
                    custom_metadata={},
                    backend_specific={
                        "vault_kv_version": 1,
                        "mount_point": self.mount_point,
                    },
                )

            # Invalidate cache
            await self.cache.invalidate_path(path)

            # Cache the new secret
            await self.cache.set_secret(
                path,
                {
                    "data": data,
                    "metadata": {
                        "created_at": secret_metadata.created_at,
                        "updated_at": secret_metadata.updated_at,
                        "version": secret_metadata.version,
                        "custom_metadata": secret_metadata.custom_metadata,
                        "backend_specific": secret_metadata.backend_specific,
                    },
                },
                version,
            )

            logger.info(f"Stored secret in Vault: {path}")
            return Secret(path, data, secret_metadata)

        except Forbidden:
            raise SecretUnauthorizedError(f"Access denied to write secret: {path}")
        except VaultError as e:
            raise SecretBackendError(f"Vault error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error storing secret {path}: {e}")
            raise SecretBackendError(f"Failed to store secret: {e}")

    async def list_secrets(self, prefix: str = "", limit: int = 100) -> List[str]:
        """
        List secrets under a given prefix.

        Args:
            prefix: Path prefix to filter secrets
            limit: Maximum number of secrets to return

        Returns:
            List of secret paths

        Raises:
            SecretUnauthorizedError: If list permissions are deniedError: If Vault
            SecretBackend is unavailable
        """
        try:
            await self._ensure_authenticated()
            kv_version = await self._detect_kv_version()

            client = await self._get_client()

            # Handle KV v1 vs v2
            if kv_version == 2:
                response = client.secrets.kv.v2.list_secrets(
                    path=prefix,
                    mount_point=self.mount_point,
                )

                if response and "data" in response and "keys" in response["data"]:
                    paths = response["data"]["keys"]
                    # Filter out directory markers and apply limit
                    secret_paths = [path for path in paths if not path.endswith("/")][
                        :limit
                    ]
                else:
                    secret_paths = []

            else:  # KV v1
                response = client.secrets.kv.v1.list_secrets(
                    path=prefix,
                    mount_point=self.mount_point,
                )

                if response and "data" in response and "keys" in response["data"]:
                    paths = response["data"]["keys"]
                    secret_paths = [path for path in paths if not path.endswith("/")][
                        :limit
                    ]
                else:
                    secret_paths = []

            logger.debug(f"Listed {len(secret_paths)} secrets under prefix: {prefix}")
            return secret_paths

        except Forbidden:
            raise SecretUnauthorizedError(
                f"Access denied to list secrets with prefix: {prefix}"
            )
        except VaultError as e:
            raise SecretBackendError(f"Vault error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing secrets with prefix {prefix}: {e}")
            raise SecretBackendError(f"Failed to list secrets: {e}")

    async def delete_secret(self, path: str, version: Optional[int] = None) -> None:
        """
        Delete a secret.

        For KV v1: Permanently deletes the secret.
        For KV v2: Soft deletes the latest version, or specific version if provided.

        Args:
            path: Secret path
            version: Optional specific version to delete (KV v2 only)

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretUnauthorizedError: If delete permissions are denied
            SecretBackendError: If Vault is unavailable
        """
        try:
            await self._ensure_authenticated()
            kv_version = await self._detect_kv_version()

            client = await self._get_client()

            # Handle KV v1 vs v2
            if kv_version == 2:
                if version is not None:
                    # Delete specific version
                    client.secrets.kv.v2.delete_secret_versions(
                        path=path,
                        versions=[version],
                        mount_point=self.mount_point,
                    )
                else:
                    # Delete latest version
                    client.secrets.kv.v2.delete_latest_version_of_secret(
                        path=path,
                        mount_point=self.mount_point,
                    )
            else:  # KV v1
                client.secrets.kv.v1.delete_secret(
                    path=path,
                    mount_point=self.mount_point,
                )

            # Invalidate cache
            await self.cache.invalidate_path(path)

            logger.info(f"Deleted secret from Vault: {path}")

        except InvalidPath:
            raise SecretNotFoundError(f"Secret not found at path: {path}")
        except Forbidden:
            raise SecretUnauthorizedError(f"Access denied to delete secret: {path}")
        except VaultError as e:
            raise SecretBackendError(f"Vault error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting secret {path}: {e}")
            raise SecretBackendError(f"Failed to delete secret: {e}")

    async def rotate_secret(self, path: str) -> str:
        """
        Rotate a secret value.

        Note: Vault doesn't have automatic rotation, so this generates
        a new secret value and updates it.

        Args:
            path: Secret path

        Returns:
            New secret value or rotation workflow ID

        Raises:
            NotImplementedError: If rotation is not supported
        """
        import secrets
        import string

        # Generate a new random secret
        alphabet = string.ascii_letters + string.digits
        new_secret = "".join(secrets.choice(alphabet) for _ in range(32))

        # Get existing secret to preserve structure
        try:
            existing_secret = await self.get_secret(path)
            new_data = existing_secret.data.copy()
            new_data["value"] = new_secret

            # Update with new value
            await self.put_secret(path, new_data)

            logger.info(f"Rotated secret: {path}")
            return new_secret

        except Exception as e:
            logger.error(f"Failed to rotate secret {path}: {e}")
            raise SecretBackendError(f"Failed to rotate secret: {e}")

    async def health(self) -> Dict[str, Any]:
        """
        Check Vault adapter health.

        Returns:
            Dictionary with health status and metadata
        """
        try:
            client = await self._get_client()

            # Test authentication
            is_authenticated = client.is_authenticated()

            # Get system health
            try:
                health = client.sys.read_health_status()
                sealed = health.get("sealed", True)
                initialized = health.get("initialized", False)
            except Exception:
                sealed = True
                initialized = False

            # Get KV version
            kv_version = await self._detect_kv_version()

            status = "healthy"
            if not is_authenticated:
                status = "degraded"
            elif sealed or not initialized:
                status = "unhealthy"

            return {
                "status": status,
                "authenticated": is_authenticated,
                "vault_sealed": sealed,
                "vault_initialized": initialized,
                "kv_version": kv_version,
                "mount_point": self.mount_point,
                "vault_url": self.vault_url,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
