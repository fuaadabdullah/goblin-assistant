"""
Vault client for secure secrets management in Goblin Assistant.
Provides secure access to API keys and sensitive configuration.
"""
import os
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path
import hvac
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class VaultClient:
    """HashiCorp Vault client for secrets management."""

    def __init__(self, vault_addr: Optional[str] = None, vault_token: Optional[str] = None):
        """Initialize Vault client.

        Args:
            vault_addr: Vault server address (defaults to VAULT_ADDR env var)
            vault_token: Vault authentication token (defaults to VAULT_TOKEN env var)
        """
        self.vault_addr = vault_addr or os.getenv('VAULT_ADDR')
        self.vault_token = vault_token or os.getenv('VAULT_TOKEN')

        if not self.vault_addr or not self.vault_token:
            raise ValueError("VAULT_ADDR and VAULT_TOKEN must be set")

        self.client = hvac.Client(
            url=self.vault_addr,
            token=self.vault_token
        )

        # Test connection
        if not self.client.is_authenticated():
            raise ConnectionError("Failed to authenticate with Vault")

        logger.info(f"Connected to Vault at {self.vault_addr}")

    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """Retrieve a secret from Vault.

        Args:
            path: Vault KV path (e.g., 'secret/goblin-assistant')
            key: Specific key to retrieve (returns all if None)

        Returns:
            Secret value(s) from Vault
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            data = response['data']['data']

            if key:
                return data.get(key)
            return data

        except Exception as e:
            logger.error(f"Failed to retrieve secret from {path}: {e}")
            raise

    def set_secret(self, path: str, secrets: Dict[str, Any]) -> bool:
        """Store secrets in Vault.

        Args:
            path: Vault KV path
            secrets: Dictionary of key-value pairs to store

        Returns:
            True if successful
        """
        try:
            self.client.secrets.kv.v2.create_or_update_secret_version(
                path=path,
                secret=secrets
            )
            logger.info(f"Successfully stored secrets at {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to store secrets at {path}: {e}")
            raise

    def list_secrets(self, path: str) -> list:
        """List all keys under a Vault path.

        Args:
            path: Vault KV path

        Returns:
            List of secret keys
        """
        try:
            response = self.client.secrets.kv.v2.list_secrets_version(path=path)
            return response['data']['keys']

        except Exception as e:
            logger.error(f"Failed to list secrets at {path}: {e}")
            raise

    @classmethod
    def load_env_from_vault(cls, vault_path: str = "secret/goblin-assistant",
                          env_file: str = ".env.vault") -> Dict[str, str]:
        """Load secrets from Vault and save to environment file.

        Args:
            vault_path: Vault KV path
            env_file: Output environment file

        Returns:
            Dictionary of loaded secrets
        """
        client = cls()
        secrets = client.get_secret(vault_path)

        # Write to env file
        env_path = Path(env_file)
        with open(env_path, 'w') as f:
            for key, value in secrets.items():
                f.write(f"{key}={value}\n")

        # Set permissions to restrict access
        env_path.chmod(0o600)

        logger.info(f"Saved {len(secrets)} secrets to {env_file}")
        return secrets

    @classmethod
    def get_provider_keys(cls, provider_name: str) -> Dict[str, str]:
        """Get API keys for a specific provider.

        Args:
            provider_name: Name of the provider (e.g., 'openai', 'anthropic')

        Returns:
            Dictionary with API key and related secrets
        """
        client = cls()
        path = f"secret/goblin-assistant/providers/{provider_name}"

        try:
            return client.get_secret(path)
        except Exception:
            logger.warning(f"No secrets found for provider: {provider_name}")
            return {}

def init_vault_from_env(env_file: str = ".env") -> Optional[VaultClient]:
    """Initialize Vault client from environment variables.

    Args:
        env_file: Environment file to load if VAULT_* vars not set

    Returns:
        VaultClient instance or None if not configured
    """
    # Try environment first
    vault_addr = os.getenv('VAULT_ADDR')
    vault_token = os.getenv('VAULT_TOKEN')

    # Load from file if not set
    if not vault_addr or not vault_token:
        if Path(env_file).exists():
            load_dotenv(env_file)
            vault_addr = os.getenv('VAULT_ADDR')
            vault_token = os.getenv('VAULT_TOKEN')

    if vault_addr and vault_token:
        try:
            return VaultClient(vault_addr, vault_token)
        except Exception as e:
            logger.warning(f"Failed to initialize Vault client: {e}")
            return None

    return None

# Convenience functions for common operations
def get_api_key(provider: str, key_name: str = "api_key") -> Optional[str]:
    """Get API key for a provider from Vault.

    Args:
        provider: Provider name
        key_name: Key name (default: 'api_key')

    Returns:
        API key or None if not found
    """
    vault = init_vault_from_env()
    if vault:
        keys = vault.get_provider_keys(provider)
        return keys.get(key_name)
    return None

def load_all_provider_keys() -> Dict[str, Dict[str, str]]:
    """Load all provider keys from Vault.

    Returns:
        Dictionary mapping provider names to their key dictionaries
    """
    vault = init_vault_from_env()
    if not vault:
        return {}

    providers = {}
    try:
        # List all provider paths
        base_path = "secret/goblin-assistant/providers"
        response = vault.client.secrets.kv.v2.list_secrets_version(path=base_path)
        provider_names = response['data']['keys']

        for provider in provider_names:
            if provider.endswith('/'):  # Directory
                provider_name = provider.rstrip('/')
                providers[provider_name] = vault.get_provider_keys(provider_name)

    except Exception as e:
        logger.error(f"Failed to load provider keys: {e}")

    return providers
