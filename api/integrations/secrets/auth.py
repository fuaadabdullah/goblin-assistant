"""
Authentication helpers for secrets adapters.

Provides common authentication mechanisms for different backends.
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AuthCredentials:
    """Base class for authentication credentials."""

    def __init__(self, credential_type: str):
        self.credential_type = credential_type
        self.created_at = datetime.utcnow()


class TokenCredentials(AuthCredentials):
    """Token-based authentication credentials."""

    def __init__(self, token: str, expires_at: Optional[datetime] = None):
        super().__init__("token")
        self.token = token
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at

    def get_time_until_expiry(self) -> timedelta:
        """Get time until token expires."""
        if self.expires_at is None:
            return timedelta.max
        return self.expires_at - datetime.utcnow()


class AppRoleCredentials(AuthCredentials):
    """HashiCorp Vault AppRole credentials."""

    def __init__(self, role_id: str, secret_id: str):
        super().__init__("approle")
        self.role_id = role_id
        self.secret_id = secret_id
        self._session_token: Optional[TokenCredentials] = None

    def get_session_token(self) -> Optional[TokenCredentials]:
        """Get the current session token."""
        return self._session_token

    def set_session_token(self, token: TokenCredentials) -> None:
        """Set the session token after login."""
        self._session_token = token

    def is_session_valid(self) -> bool:
        """Check if session token is valid."""
        if self._session_token is None:
            return False
        return not self._session_token.is_expired()


class AuthManager:
    """Manages authentication for secrets backends."""

    def __init__(self):
        self._credentials_store: Dict[str, AuthCredentials] = {}
        self._renewal_tasks: Dict[str, asyncio.Task] = {}

    def store_credentials(self, name: str, credentials: AuthCredentials) -> None:
        """
        Store authentication credentials.

        Args:
            name: Identifier for the credentials
            credentials: The credentials to store
        """
        self._credentials_store[name] = credentials
        logger.debug(f"Stored credentials for: {name}")

    def get_credentials(self, name: str) -> Optional[AuthCredentials]:
        """
        Retrieve stored credentials.

        Args:
            name: Identifier for the credentials

        Returns:
            The stored credentials or None
        """
        return self._credentials_store.get(name)

    async def rotate_credentials(
        self, name: str, new_credentials: AuthCredentials
    ) -> None:
        """
        Rotate stored credentials.

        Args:
            name: Identifier for the credentials
            new_credentials: The new credentials
        """
        old_credentials = self._credentials_store.get(name)
        self._credentials_store[name] = new_credentials

        # Cancel any existing renewal tasks
        if name in self._renewal_tasks:
            self._renewal_tasks[name].cancel()
            del self._renewal_tasks[name]

        logger.info(f"Rotated credentials for: {name}")

        # If old credentials had renewal tasks, stop them
        if old_credentials and hasattr(old_credentials, "stop_renewal"):
            if name in self._renewal_tasks:
                self._renewal_tasks[name].cancel()

    def start_token_renewal(
        self,
        name: str,
        renewal_func,
        interval_seconds: int = 300,
    ) -> None:
        """
        Start automatic token renewal.

        Args:
            name: Identifier for the credentials
            renewal_func: Async function to call for renewal
            interval_seconds: Renewal interval in seconds
        """
        if name in self._renewal_tasks:
            self._renewal_tasks[name].cancel()

        self._renewal_tasks[name] = asyncio.create_task(
            self._renewal_loop(name, renewal_func, interval_seconds)
        )
        logger.debug(f"Started token renewal for: {name}")

    async def _renewal_loop(
        self,
        name: str,
        renewal_func,
        interval_seconds: int,
    ) -> None:
        """
        Background task for token renewal.

        Args:
            name: Identifier for the credentials
            renewal_func: Async function to call for renewal
            interval_seconds: Renewal interval in seconds
        """
        try:
            while True:
                await asyncio.sleep(interval_seconds)

                credentials = self._credentials_store.get(name)
                if not credentials:
                    logger.warning(f"No credentials found for renewal: {name}")
                    continue

                # Check if renewal is needed (renew at 75% of lifetime)
                if isinstance(credentials, TokenCredentials):
                    time_until_expiry = credentials.get_time_until_expiry()
                    renewal_threshold = timedelta(seconds=interval_seconds * 1.5)

                    if time_until_expiry <= renewal_threshold:
                        logger.info(f"Renewing token for: {name}")
                        try:
                            await renewal_func(name, credentials)
                        except Exception as e:
                            logger.error(f"Token renewal failed for {name}: {e}")
                elif isinstance(credentials, AppRoleCredentials):
                    # Handle AppRole token renewal
                    if not credentials.is_session_valid():
                        logger.info(f"Renewing AppRole session for: {name}")
                        try:
                            await renewal_func(name, credentials)
                        except Exception as e:
                            logger.error(f"AppRole renewal failed for {name}: {e}")

        except asyncio.CancelledError:
            logger.debug(f"Token renewal cancelled for: {name}")
        except Exception as e:
            logger.error(f"Token renewal error for {name}: {e}")

    def stop_renewal(self, name: str) -> None:
        """
        Stop token renewal for a credential.

        Args:
            name: Identifier for the credentials
        """
        if name in self._renewal_tasks:
            self._renewal_tasks[name].cancel()
            del self._renewal_tasks[name]
            logger.debug(f"Stopped token renewal for: {name}")

    async def stop_all_renewals(self) -> None:
        """Stop all token renewal tasks."""
        for name in list(self._renewal_tasks.keys()):
            self.stop_renewal(name)

    def cleanup_credentials(self, name: str) -> None:
        """
        Remove stored credentials and stop renewal.

        Args:
            name: Identifier for the credentials
        """
        self.stop_renewal(name)
        if name in self._credentials_store:
            del self._credentials_store[name]
            logger.debug(f"Cleaned up credentials for: {name}")


# Global auth manager instance
_auth_manager = AuthManager()


def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance."""
    return _auth_manager


async def refresh_vault_token(
    credentials_name: str, credentials: AppRoleCredentials
) -> None:
    """
    Refresh HashiCorp Vault token using AppRole.

    Args:
        credentials_name: Name of the stored credentials
        credentials: AppRole credentials
    """
    from .vault_adapter import VaultAdapter

    adapter = VaultAdapter()
    token_credentials = await adapter.authenticate_with_approle(
        role_id=credentials.role_id,
        secret_id=credentials.secret_id,
    )
    credentials.set_session_token(token_credentials)
    get_auth_manager().store_credentials(credentials_name, credentials)
    logger.info(f"Refreshed Vault AppRole token for: {credentials_name}")


def setup_vault_approle_renewal(
    name: str,
    credentials: AppRoleCredentials,
    vault_client,
    interval_seconds: int = 300,
) -> None:
    """
    Setup automatic renewal for Vault AppRole tokens.

    Args:
        name: Identifier for the credentials
        credentials: AppRole credentials
        vault_client: Vault client instance
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
    vault_client,
    interval_seconds: int = 300,
) -> None:
    """
    Setup automatic renewal for Vault token.

    Args:
        name: Identifier for the credentials
        credentials: Token credentials
        vault_client: Vault client instance
        interval_seconds: Renewal interval in seconds
    """
    auth_manager = get_auth_manager()
    auth_manager.store_credentials(name, credentials)

    async def renewal_func(creds_name: str, creds: TokenCredentials):
        """Renew Vault token."""
        # This will be implemented in vault_adapter.py
        # For now, just log the renewal attempt
        logger.info(f"Would renew Vault token for {creds_name}")

    auth_manager.start_token_renewal(name, renewal_func, interval_seconds)
