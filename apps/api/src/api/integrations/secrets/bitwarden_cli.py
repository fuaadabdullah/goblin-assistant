"""Bitwarden CLI subprocess execution wrapper."""

import asyncio
import logging
import os
import subprocess
from typing import List, Optional

from .base import SecretBackendError, SecretNotFoundError, SecretUnauthorizedError

logger = logging.getLogger(__name__)


async def run_bw_command(
    command: List[str],
    *,
    session_token: Optional[str] = None,
    server_url: Optional[str] = None,
    input_data: Optional[str] = None,
    capture_output: bool = True,
    timeout: int = 30,
) -> str:
    """
    Run a Bitwarden CLI command asynchronously.

    Args:
        command: Command arguments for bw CLI (e.g., ["get", "item", "name"])
        session_token: Optional session token for authentication
        server_url: Optional custom Bitwarden server URL
        input_data: Optional stdin data
        capture_output: Whether to capture stdout
        timeout: Command timeout in seconds

    Returns:
        Command output

    Raises:
        SecretBackendError: If command fails or times out
        SecretNotFoundError: If item not found
        SecretUnauthorizedError: If authentication failed
    """
    full_command = ["bw"] + command

    # Build environment
    env = os.environ.copy()
    if session_token:
        env["BW_SESSION"] = session_token
    if server_url and server_url != "https://vault.bitwarden.com":
        env["BW_SERVER"] = server_url

    try:
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *full_command,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Write input if provided
        if input_data:
            process.stdin.write(input_data.encode())
            await process.stdin.drain()
            process.stdin.close()

        # Wait for completion
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        returncode = await process.wait()

        if returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            # Map stderr patterns to typed exceptions
            if "not logged in" in error_msg.lower() or "unauthorized" in error_msg.lower():
                raise SecretUnauthorizedError(f"Bitwarden authentication failed: {error_msg}")
            elif "not found" in error_msg.lower():
                raise SecretNotFoundError(f"Item not found: {error_msg}")
            else:
                raise SecretBackendError(f"Bitwarden CLI error: {error_msg}")

        return stdout.decode().strip() if stdout else ""

    except asyncio.TimeoutError:
        raise SecretBackendError(f"Bitwarden CLI command timed out after {timeout}s")
    except FileNotFoundError:
        raise SecretBackendError("Bitwarden CLI (bw) not found. Please install it first.")
