"""
API Key Store Abstraction Layer

Provides a unified interface for storing and retrieving API keys
across different environments (development, production).
"""

from abc import ABC, abstractmethod
from typing import Optional
import os
import json
import warnings
from pathlib import Path


class APIKeyStore(ABC):
    """Abstract base class for API key storage implementations."""

    @abstractmethod
    async def get(self, provider: str) -> Optional[str]:
        """Retrieve an API key for the given provider."""
        pass

    @abstractmethod
    async def set(self, provider: str, key: str) -> None:
        """Store an API key for the given provider."""
        pass


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
        if not self.path.exists():
            return None
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
                return data.get(provider)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    async def set(self, provider: str, key: str) -> None:
        """Store API key in JSON file."""
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


class SecretManagerAPIKeyStore(APIKeyStore):
    """Production store using Bitwarden/Vault or other secret managers."""

    def __init__(self, vault_url: Optional[str] = None, token: Optional[str] = None):
        self.vault_url = vault_url or os.getenv("VAULT_URL")
        self.token = token or os.getenv("VAULT_TOKEN")
        if not self.vault_url or not self.token:
            raise ValueError(
                "SecretManagerAPIKeyStore requires VAULT_URL and VAULT_TOKEN "
                "environment variables or explicit parameters"
            )

    async def get(self, provider: str) -> Optional[str]:
        """Retrieve API key from secret manager."""
        # TODO: Implement actual secret manager integration
        # This is a placeholder for Bitwarden, HashiCorp Vault, or similar
        #
        # Example implementation for Bitwarden CLI:
        # import subprocess
        # result = subprocess.run(
        #     ["bw", "get", "item", provider],
        #     capture_output=True, text=True
        # )
        # if result.returncode == 0:
        #     return json.loads(result.stdout).get("notes", "").strip()
        #
        # Example implementation for HashiCorp Vault:
        # import hvac
        # client = hvac.Client(url=self.vault_url, token=self.token)
        # secret = client.secrets.kv.v2.read_secret_version(path=f"api-keys/{provider}")
        # return secret["data"]["data"].get("key")

        # Placeholder implementation - replace with actual secret manager logic
        raise NotImplementedError(
            "SecretManagerAPIKeyStore requires implementation for your secret manager. "
            "See comments in the code for integration examples."
        )

    async def set(self, provider: str, key: str) -> None:
        """Store API key in secret manager."""
        # TODO: Implement actual secret manager integration
        # This is a placeholder for Bitwarden, HashiCorp Vault, or similar
        raise NotImplementedError(
            "SecretManagerAPIKeyStore set() method requires implementation for your secret manager."
        )


# Factory function to create appropriate store based on environment
def create_api_key_store() -> APIKeyStore:
    """Factory function that returns the appropriate API key store for the current environment."""
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        return SecretManagerAPIKeyStore()
    else:
        return FileAPIKeyStore()
