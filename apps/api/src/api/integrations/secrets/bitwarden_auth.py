"""Bitwarden session and authentication management."""

import logging
import re
from typing import Callable, Optional

from .base import SecretBackendError, SecretUnauthorizedError

logger = logging.getLogger(__name__)


async def ensure_authenticated(
    run_bw_fn: Callable,
    session_token: Optional[str],
    server_url: Optional[str],
    timeout: int = 30,
) -> bool:
    """
    Verify that Bitwarden CLI is authenticated.

    Args:
        run_bw_fn: Function to run bw commands
        session_token: Current session token
        server_url: Bitwarden server URL
        timeout: Command timeout in seconds

    Returns:
        True if authenticated

    Raises:
        SecretUnauthorizedError: If not authenticated
    """
    try:
        await run_bw_fn(
            ["status"],
            session_token=session_token,
            server_url=server_url,
            timeout=timeout,
        )
        logger.info("Bitwarden CLI authentication verified")
        return True
    except SecretUnauthorizedError:
        raise SecretUnauthorizedError("Bitwarden CLI is not authenticated. Please login first.")


async def authenticate_with_session_token(
    run_bw_fn: Callable,
    auth_manager,
    cache,
    token: str,
    server_url: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Authenticate using a session token.

    Args:
        run_bw_fn: Function to run bw commands
        auth_manager: Credentials manager
        cache: Secret cache
        token: Bitwarden session token
        server_url: Bitwarden server URL
        timeout: Command timeout in seconds

    Returns:
        Session token

    Raises:
        SecretUnauthorizedError: If token is invalid
    """
    # Verify token works
    await ensure_authenticated(run_bw_fn, token, server_url, timeout)

    # Store credentials
    from .auth import TokenCredentials

    credentials = TokenCredentials(token)
    auth_manager.store_credentials(f"bitwarden-{server_url or 'default'}", credentials)

    # Start cache
    await cache.start()

    logger.info("Successfully authenticated with Bitwarden session token")
    return token


async def authenticate_with_login(
    run_bw_fn: Callable,
    auth_manager,
    cache,
    email: str,
    password: Optional[str] = None,
    code: Optional[str] = None,
    server_url: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Authenticate using email/password with optional 2FA.

    Args:
        run_bw_fn: Function to run bw commands
        auth_manager: Credentials manager
        cache: Secret cache
        email: Bitwarden account email
        password: Account password
        code: Optional 2FA code
        server_url: Bitwarden server URL
        timeout: Command timeout in seconds

    Returns:
        Session token

    Raises:
        SecretBackendError: If login fails
    """
    try:
        if not password:
            raise SecretBackendError(
                "Interactive login not supported. Please provide password and optional 2FA code."
            )

        # Build login command
        login_cmd = ["login", email, "--password", password]
        if code:
            login_cmd.extend(["--code", code])

        # Execute login
        output = await run_bw_fn(
            login_cmd,
            server_url=server_url,
            capture_output=False,
            timeout=timeout,
        )

        # Extract session token from output
        session_token = None
        if output and not output.startswith("You are logged in"):
            token_match = re.search(r'export BW_SESSION="([^"]+)"', output)
            if token_match:
                session_token = token_match.group(1)

        # Try to unlock vault
        if password:
            try:
                await unlock_vault(run_bw_fn, password, server_url, timeout)
            except Exception:
                logger.warning("Could not unlock vault after login")

        logger.info("Successfully logged in to Bitwarden")
        return session_token or ""

    except Exception as e:
        raise SecretBackendError(f"Bitwarden login failed: {e}")


async def unlock_vault(
    run_bw_fn: Callable,
    password: str,
    server_url: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Unlock the vault with master password.

    Args:
        run_bw_fn: Function to run bw commands
        password: Master password
        server_url: Bitwarden server URL
        timeout: Command timeout in seconds

    Returns:
        Session token

    Raises:
        SecretBackendError: If unlock fails
    """
    try:
        output = await run_bw_fn(
            ["unlock", password],
            server_url=server_url,
            timeout=timeout,
        )

        # Extract session token
        token_match = re.search(r'export BW_SESSION="([^"]+)"', output)
        if token_match:
            session_token = token_match.group(1)
            logger.info("Bitwarden vault unlocked")
            return session_token
        else:
            raise SecretBackendError("Could not extract session token from unlock")

    except Exception as e:
        raise SecretBackendError(f"Vault unlock failed: {e}")
