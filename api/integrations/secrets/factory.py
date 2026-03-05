"""
Factory module for creating secrets adapters.

Provides a unified interface to create and configure adapters
for different secrets backends like Vault and Bitwarden.
"""

import logging
from typing import Dict, Any, Optional, Type
from .base import SecretAdapter, SecretAdapterError
from .vault_adapter import VaultAdapter
from .bitwarden_adapter import BitwardenAdapter

logger = logging.getLogger(__name__)


class AdapterFactory:
    """Factory for creating secrets adapters based on configuration."""

    _adapters: Dict[str, Type[SecretAdapter]] = {
        "vault": VaultAdapter,
        "bitwarden": BitwardenAdapter,
    }

    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[SecretAdapter]) -> None:
        """
        Register a new adapter type.

        Args:
            name: Name identifier for the adapter
            adapter_class: The adapter class to register
        """
        cls._adapters[name] = adapter_class
        logger.info(f"Registered adapter: {name}")

    @classmethod
    def create_adapter(
        cls,
        adapter_type: str,
        **kwargs,
    ) -> SecretAdapter:
        """
        Create a secrets adapter instance.

        Args:
            adapter_type: Type of adapter to create ("vault", "bitwarden", etc.)
            **kwargs: Configuration parameters for the adapter

        Returns:
            Configured adapter instance

        Raises:
            SecretAdapterError: If adapter type is not supported
        """
        if adapter_type not in cls._adapters:
            available_types = list(cls._adapters.keys())
            raise SecretAdapterError(
                f"Unsupported adapter type: {adapter_type}. "
                f"Available types: {available_types}"
            )

        adapter_class = cls._adapters[adapter_type]
        logger.info(f"Creating {adapter_type} adapter with config: {kwargs}")

        return adapter_class(**kwargs)


# Global factory instance
_factory = AdapterFactory()


def create_adapter(adapter_type: str, **kwargs) -> SecretAdapter:
    """
    Create a secrets adapter using the global factory.

    Args:
        adapter_type: Type of adapter to create
        **kwargs: Configuration parameters

    Returns:
        Configured adapter instance
    """
    return _factory.create_adapter(adapter_type, **kwargs)


def get_available_adapters() -> list:
    """
    Get list of available adapter types.

    Returns:
        List of available adapter type names
    """
    return list(_factory._adapters.keys())


def register_adapter(name: str, adapter_class: Type[SecretAdapter]) -> None:
    """
    Register a new adapter type globally.

    Args:
        name: Name identifier for the adapter
        adapter_class: The adapter class to register
    """
    _factory.register_adapter(name, adapter_class)


# Convenience functions for common adapter types
def create_vault_adapter(
    vault_url: str,
    mount_point: str = "secret",
    verify_ssl: bool = True,
    timeout: int = 30,
    cache_ttl: int = 300,
    cache_size: int = 1000,
) -> VaultAdapter:
    """
    Create a Vault adapter with common configuration.

    Args:
        vault_url: Vault server URL
        mount_point: KV engine mount point
        verify_ssl: Whether to verify SSL certificates
        timeout: Request timeout in seconds
        cache_ttl: Cache time-to-live in seconds
        cache_size: Maximum cache entries

    Returns:
        Configured VaultAdapter instance
    """
    return create_adapter(
        "vault",
        vault_url=vault_url,
        mount_point=mount_point,
        verify_ssl=verify_ssl,
        timeout=timeout,
        cache_ttl=cache_ttl,
        cache_size=cache_size,
    )


def create_bitwarden_adapter(
    session_token: Optional[str] = None,
    server_url: Optional[str] = None,
    cache_ttl: int = 300,
    cache_size: int = 1000,
    timeout: int = 30,
) -> BitwardenAdapter:
    """
    Create a Bitwarden adapter with common configuration.

    Args:
        session_token: Optional pre-existing session token
        server_url: Optional custom Bitwarden server URL
        cache_ttl: Cache time-to-live in seconds
        cache_size: Maximum cache entries
        timeout: Command timeout in seconds

    Returns:
        Configured BitwardenAdapter instance
    """
    return create_adapter(
        "bitwarden",
        session_token=session_token,
        server_url=server_url,
        cache_ttl=cache_ttl,
        cache_size=cache_size,
        timeout=timeout,
    )
