"""Compatibility exports and Vault credential renewal orchestration."""

import logging
import os

from .credentials import (
    AppRoleCredentials,
    AuthCredentials,
    AuthManager,
    TokenCredentials,
    get_auth_manager,
)

__all__ = [
    "AppRoleCredentials",
    "AuthCredentials",
    "AuthManager",
    "TokenCredentials",
    "get_auth_manager",
    "refresh_vault_token",
    "setup_vault_approle_renewal",
    "setup_vault_token_renewal",
]
logger = logging.getLogger(__name__)


async def refresh_vault_token(credentials_name: str, credentials: AppRoleCredentials) -> None:
    """
    Refresh HashiCorp Vault token using AppRole.

    Args:
        credentials_name: Name of the stored credentials
        credentials: AppRole credentials
    """
    from .vault_adapter import VaultAdapter

    vault_url = os.environ.get("VAULT_ADDR")
    if not vault_url:
        raise ValueError("VAULT_ADDR is required for Vault token renewal")
    adapter = VaultAdapter(vault_url=vault_url)
    try:
        token_credentials = await adapter.authenticate_with_approle(
            role_id=credentials.role_id,
            secret_id=credentials.secret_id,
        )
    finally:
        await adapter.close()
    credentials.set_session_token(token_credentials)
    get_auth_manager().store_credentials(credentials_name, credentials)
    logger.info("Refreshed Vault AppRole token for: %s", credentials_name)


def setup_vault_approle_renewal(
    name: str,
    credentials: AppRoleCredentials,
    interval_seconds: int = 300,
) -> None:
    """
    Setup automatic renewal for Vault AppRole tokens.

    Args:
        name: Identifier for the credentials
        credentials: AppRole credentials
        interval_seconds: Renewal interval in seconds
    """
    auth_manager = get_auth_manager()
    auth_manager.store_credentials(name, credentials)

    async def renewal_func(creds_name: str, creds: AppRoleCredentials):
        """Renew Vault AppRole token via VaultAdapter."""
        await refresh_vault_token(creds_name, creds)

    auth_manager.start_token_renewal(name, renewal_func, interval_seconds)


def setup_vault_token_renewal(
    name: str,
    credentials: TokenCredentials,
    interval_seconds: int = 300,
) -> None:
    """
    Setup automatic renewal for Vault token.

    Args:
        name: Identifier for the credentials
        credentials: Token credentials
        interval_seconds: Renewal interval in seconds
    """
    auth_manager = get_auth_manager()
    auth_manager.store_credentials(name, credentials)

    async def renewal_func(creds_name: str, creds: TokenCredentials):
        """Renew Vault token."""
        # This will be implemented in vault_adapter.py
        # For now, just log the renewal attempt
        logger.info("Would renew Vault token for %s", creds_name)

    auth_manager.start_token_renewal(name, renewal_func, interval_seconds)
