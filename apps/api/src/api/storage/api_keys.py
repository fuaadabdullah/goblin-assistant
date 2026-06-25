"""
API Key Store Abstraction Layer

Provides a unified interface for storing and retrieving API keys
across different environments (development, production).
"""

import asyncio
import json
import os
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class APIKeyStore(ABC):
    """Abstract base class for API key storage implementations."""

    @abstractmethod
    async def get(self, provider: str) -> Optional[str]:
        """Retrieve an API key for the given provider."""
        ...

    @abstractmethod
    async def set(self, provider: str, key: str) -> None:
        """Store an API key for the given provider."""
        ...


class FileAPIKeyStore(APIKeyStore):
    """Development-only file-based store with production warnings."""

    def __init__(self, path: str = "api_keys.json"):
        self.path = Path(path)
        if os.getenv("ENVIRONMENT") == "production":
            warnings.warn(
                "Using file-based API key store in production is insecure! "
                "Use SecretManagerAPIKeyStore instead.",
                UserWarning,
                stacklevel=2,
            )

    async def get(self, provider: str) -> Optional[str]:
        """Get API key from JSON file."""

        def _read() -> Optional[str]:
            if not self.path.exists():
                return None
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                    return data.get(provider)
            except (FileNotFoundError, json.JSONDecodeError):
                return None

        return await asyncio.to_thread(_read)

    async def set(self, provider: str, key: str) -> None:
        """Store API key in JSON file."""

        def _write() -> None:
            data = {}
            if self.path.exists():
                try:
                    with open(self.path, "r") as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    data = {}

            data[provider] = key

            with open(self.path, "w") as f:
                json.dump(data, f, indent=2)

        await asyncio.to_thread(_write)


class SecretManagerAPIKeyStore(APIKeyStore):
    """Production store using HashiCorp Vault KV v2."""

    def __init__(self, vault_url: Optional[str] = None, token: Optional[str] = None):
        self.vault_url = vault_url or os.getenv("VAULT_URL")
        self.token = token or os.getenv("VAULT_TOKEN")
        if not self.vault_url or not self.token:
            raise ValueError(
                "SecretManagerAPIKeyStore requires VAULT_URL and VAULT_TOKEN "
                "environment variables or explicit parameters"
            )

    def _get_client(self):
        try:
            import hvac  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "hvac package is required for SecretManagerAPIKeyStore. "
                "Install it with: pip install hvac"
            ) from exc
        client = hvac.Client(url=self.vault_url, token=self.token)
        if not client.is_authenticated():
            raise PermissionError("Vault authentication failed — check VAULT_TOKEN")
        return client

    async def get(self, provider: str) -> Optional[str]:
        """Retrieve API key from Vault KV v2 at path api-keys/{provider}."""

        def _read():
            client = self._get_client()
            secret = client.secrets.kv.v2.read_secret_version(
                path=f"api-keys/{provider}",
                raise_on_deleted_version=False,
            )
            return secret["data"]["data"].get("key")

        try:
            return await asyncio.to_thread(_read)
        except Exception as exc:
            if "404" in str(exc) or "InvalidPath" in type(exc).__name__:
                return None
            raise

    async def set(self, provider: str, key: str) -> None:
        """Store API key in Vault KV v2 at path api-keys/{provider}."""

        def _write():
            client = self._get_client()
            client.secrets.kv.v2.create_or_update_secret(
                path=f"api-keys/{provider}",
                secret={"key": key},
            )

        await asyncio.to_thread(_write)


# Factory function to create appropriate store based on environment
def create_api_key_store() -> APIKeyStore:
    """Factory function that returns the appropriate API key store for the current environment."""
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        return SecretManagerAPIKeyStore()
    else:
        return FileAPIKeyStore()
