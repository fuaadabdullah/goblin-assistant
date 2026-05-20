"""
Bitwarden adapter for secrets management using Bitwarden CLI.

Provides async interface to Bitwarden using the bw CLI tool.
Supports authentication via session tokens and login.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import os
import re

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
from .auth import TokenCredentials, get_auth_manager

logger = logging.getLogger(__name__)


def _parse_bw_time(time_str: Optional[str]) -> Optional[datetime]:
    """Parse Bitwarden timestamp string to datetime object."""
    if not time_str:
        return None
    try:
        # Bitwarden uses ISO 8601 format
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except Exception:
        return None


class BitwardenAdapter(SecretAdapter):
    """
    Bitwarden adapter for secrets operations using CLI.

    Maps Bitwarden items to secret paths, with folder/collection support.
    Uses subprocess to call bw CLI commands.
    """

    def __init__(
        self,
        session_token: Optional[str] = None,
        server_url: Optional[str] = None,
        cache_ttl: int = 300,
        cache_size: int = 1000,
        timeout: int = 30,
    ):
        """
        Initialize Bitwarden adapter.

        Args:
            session_token: Optional pre-existing session token
            server_url: Optional custom Bitwarden server URL
            cache_ttl: Cache time-to-live in seconds
            cache_size: Maximum cache entries
            timeout: Command timeout in seconds
        """
        self.session_token = session_token
        self.server_url = server_url or "https://vault.bitwarden.com"
        self.timeout = timeout
        self._authenticated = False

        # Initialize cache
        self.cache = SecretCache(max_size=cache_size, default_ttl=cache_ttl)

        # Auth manager
        self.auth_manager = get_auth_manager()

    async def _run_bw_command(
        self,
        command: List[str],
        input_data: Optional[str] = None,
        capture_output: bool = True,
    ) -> str:
        """
        Run a Bitwarden CLI command.

        Args:
            command: Command arguments for bw CLI
            input_data: Optional stdin data
            capture_output: Whether to capture stdout

        Returns:
            Command output

        Raises:
            SecretBackendError: If command fails
        """
        # Build full command
        full_command = ["bw"] + command

        # Set environment with session token if available
        env = os.environ.copy()
        if self.session_token:
            env["BW_SESSION"] = self.session_token

        # Add server URL if custom
        if self.server_url != "https://vault.bitwarden.com":
            env["BW_SERVER"] = self.server_url

        try:
            # Run command asynchronously
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
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )

            returncode = await process.wait()

            if returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                # Check for specific error conditions
                if (
                    "not logged in" in error_msg.lower()
                    or "unauthorized" in error_msg.lower()
                ):
                    raise SecretUnauthorizedError(
                        f"Bitwarden authentication failed: {error_msg}"
                    )
                elif "not found" in error_msg.lower():
                    raise SecretNotFoundError(f"Item not found: {error_msg}")
                else:
                    raise SecretBackendError(f"Bitwarden CLI error: {error_msg}")

            return stdout.decode().strip() if stdout else ""

        except asyncio.TimeoutError:
            raise SecretBackendError(
                f"Bitwarden CLI command timed out after {self.timeout}s"
            )
        except FileNotFoundError:
            raise SecretBackendError(
                "Bitwarden CLI (bw) not found. Please install it first."
            )

    async def _ensure_authenticated(self) -> None:
        """Ensure Bitwarden CLI is authenticated."""
        if not self._authenticated:
            try:
                # Test authentication with status command
                await self._run_bw_command(["status"])
                self._authenticated = True
                logger.info("Bitwarden CLI authentication verified")
            except SecretUnauthorizedError:
                raise SecretUnauthorizedError(
                    "Bitwarden CLI is not authenticated. Please login first."
                )

    async def authenticate_with_session_token(self, token: str) -> None:
        """
        Authenticate using a session token.

        Args:
            token: Bitwarden session token
        """
        self.session_token = token
        self._authenticated = False  # Reset to verify

        # Test the token
        await self._ensure_authenticated()

        # Store credentials for management
        credentials = TokenCredentials(token)
        self.auth_manager.store_credentials(f"bitwarden-{self.server_url}", credentials)

        # Start cache if not already started
        await self.cache.start()

        logger.info("Successfully authenticated with Bitwarden session token")

    async def authenticate_with_login(
        self,
        email: str,
        password: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        """
        Authenticate using email/password with optional 2FA.

        Args:
            email: Bitwarden account email
            password: Account password (prompted if not provided)
            code: Optional 2FA code
        """
        try:
            # Build login command
            login_cmd = ["login", email]

            if password:
                # Use non-interactive login
                login_cmd.extend(["--password", password])
                if code:
                    login_cmd.extend(["--code", code])
            else:
                # Interactive login - this won't work in async context
                raise SecretBackendError(
                    "Interactive login not supported. Please provide password and optional 2FA code."
                )

            # Execute login
            output = await self._run_bw_command(login_cmd, capture_output=False)

            # Extract session token from output if available
            # Note: bw login outputs the session token to stdout in some versions
            if output and not output.startswith("You are logged in"):
                # Try to extract session token
                token_match = re.search(r'export BW_SESSION="([^"]+)"', output)
                if token_match:
                    self.session_token = token_match.group(1)

            # Unlock vault (may be needed after login)
            try:
                await self.unlock_vault(password)
            except Exception:
                logger.warning("Could not unlock vault after login")

            self._authenticated = True
            logger.info("Successfully logged in to Bitwarden")

        except Exception as e:
            raise SecretBackendError(f"Bitwarden login failed: {e}")

    async def unlock_vault(self, password: str) -> None:
        """
        Unlock the vault with master password.

        Args:
            password: Master password
        """
        try:
            output = await self._run_bw_command(["unlock", password])

            # Extract session token
            token_match = re.search(r'export BW_SESSION="([^"]+)"', output)
            if token_match:
                self.session_token = token_match.group(1)
                self._authenticated = True
                logger.info("Bitwarden vault unlocked")
            else:
                raise SecretBackendError("Could not extract session token from unlock")

        except Exception as e:
            raise SecretBackendError(f"Vault unlock failed: {e}")

    def _path_to_item_id(self, path: str) -> tuple[str, Optional[str]]:
        """
        Convert secret path to Bitwarden item ID and field name.

        Path format: "folder/item" or "folder/item.field"
        Returns: (item_id_or_name, field_name)
        """
        parts = path.split(".")
        item_path = parts[0]
        field_name = parts[1] if len(parts) > 1 else None

        return item_path, field_name

    def _item_to_secret(
        self, item: Dict[str, Any], field_name: Optional[str] = None
    ) -> Secret:
        """
        Convert Bitwarden item to Secret object.

        Args:
            item: Bitwarden item data
            field_name: Optional specific field name

        Returns:
            Secret object
        """
        # Extract data based on field_name
        if field_name:
            # Return specific field
            if field_name in item.get("fields", {}):
                secret_data = {"value": item["fields"][field_name]}
            elif field_name == "username":
                secret_data = {"value": item.get("login", {}).get("username", "")}
            elif field_name == "password":
                secret_data = {"value": item.get("login", {}).get("password", "")}
            elif field_name == "totp":
                secret_data = {"value": item.get("login", {}).get("totp", "")}
            else:
                secret_data = {"value": ""}
        else:
            # Return entire item as structured data
            secret_data = {
                "name": item.get("name", ""),
                "username": item.get("login", {}).get("username", ""),
                "password": item.get("login", {}).get("password", ""),
                "uri": item.get("login", {}).get("uris", [{}])[0].get("uri", "")
                if item.get("login", {}).get("uris")
                else "",
                "notes": item.get("notes", ""),
                "totp": item.get("login", {}).get("totp", ""),
            }
            # Add custom fields
            for field in item.get("fields", []):
                secret_data[field["name"]] = field.get("value", "")

        # Create metadata
        metadata = SecretMetadata(
            created_at=_parse_bw_time(item.get("creationDate")),
            updated_at=_parse_bw_time(item.get("revisionDate")),
            custom_metadata={
                "item_id": item.get("id"),
                "organization_id": item.get("organizationId"),
                "collection_ids": item.get("collectionIds", []),
                "folder_id": item.get("folderId"),
                "type": item.get("type"),
                "favorite": item.get("favorite", False),
            },
            backend_specific={
                "bitwarden_item_id": item.get("id"),
                "bitwarden_type": item.get("type"),
                "bitwarden_folder_id": item.get("folderId"),
            },
        )

        return Secret(
            path=f"{item.get('folderId', 'root')}/{item.get('name', item.get('id'))}",
            data=secret_data,
            metadata=metadata,
        )

    async def get_secret(self, path: str, version: Optional[int] = None) -> Secret:
        """
        Retrieve secret from Bitwarden.

        Args:
            path: Secret path (format: "folder/item" or "folder/item.field")
            version: Not supported by Bitwarden (ignored)

        Returns:
            Secret object

        Raises:
            SecretNotFoundError: If item doesn't exist
            SecretUnauthorizedError: If authentication fails
            SecretBackendError: If CLI fails
        """
        try:
            await self._ensure_authenticated()

            # Check cache first
            cached_secret = await self.cache.get_secret(path, version)
            if cached_secret is not None:
                logger.debug(f"Cache hit for secret: {path}")
                return Secret(
                    path,
                    cached_secret["data"],
                    SecretMetadata(**cached_secret["metadata"]),
                )

            item_path, field_name = self._path_to_item_id(path)

            # Get item by name or ID
            try:
                # Try to get by exact name first
                output = await self._run_bw_command(["get", "item", item_path])
                item = json.loads(output)
            except SecretNotFoundError:
                # If not found by name, try to list and find
                try:
                    list_output = await self._run_bw_command(
                        ["list", "items", "--search", item_path]
                    )
                    items = json.loads(list_output)
                    if not items:
                        raise SecretNotFoundError(f"Item not found: {path}")

                    # Use first match
                    item = items[0]
                except Exception:
                    raise SecretNotFoundError(f"Item not found: {path}")

            secret = self._item_to_secret(item, field_name)

            # Cache the result
            await self.cache.set_secret(
                path,
                {
                    "data": secret.data,
                    "metadata": {
                        "created_at": secret.metadata.created_at,
                        "updated_at": secret.metadata.updated_at,
                        "version": secret.metadata.version,
                        "custom_metadata": secret.metadata.custom_metadata,
                        "backend_specific": secret.metadata.backend_specific,
                    },
                },
                version,
            )

            logger.info(f"Retrieved secret from Bitwarden: {path}")
            return secret

        except json.JSONDecodeError as e:
            raise SecretBackendError(f"Invalid JSON response from Bitwarden CLI: {e}")
        except Exception as e:
            if isinstance(
                e, (SecretNotFoundError, SecretUnauthorizedError, SecretBackendError)
            ):
                raise
            raise SecretBackendError(f"Failed to retrieve secret: {e}")

    async def put_secret(
        self,
        path: str,
        data: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        version: Optional[int] = None,
    ) -> Secret:
        """
        Create or update a secret in Bitwarden.

        Args:
            path: Secret path (format: "folder/item")
            data: Secret data
            metadata: Optional metadata (not supported by CLI)
            version: Not supported (ignored)

        Returns:
            Secret object representing the stored secret

        Raises:
            SecretValidationError: If data validation fails
            SecretUnauthorizedError: If write permissions are denied
            SecretBackendError: If CLI fails
        """
        try:
            await self._ensure_authenticated()

            # Validate data
            if not data:
                raise SecretValidationError("Secret data cannot be empty")

            item_path, field_name = self._path_to_item_id(path)

            if field_name:
                # Updating a specific field - not supported by CLI
                raise SecretBackendError(
                    "Updating specific fields not supported via Bitwarden CLI"
                )

            # Parse folder and item name
            path_parts = item_path.split("/")
            folder_name = path_parts[0] if len(path_parts) > 1 else None
            item_name = path_parts[-1]

            # Get folder ID if folder specified
            folder_id = None
            if folder_name:
                try:
                    folders_output = await self._run_bw_command(["list", "folders"])
                    folders = json.loads(folders_output)
                    for folder in folders:
                        if folder.get("name") == folder_name:
                            folder_id = folder["id"]
                            break
                except Exception:
                    logger.warning(f"Could not find folder: {folder_name}")

            # Create item JSON
            item_data = {
                "type": 1,  # Login item type
                "name": item_name,
                "notes": data.get("notes", ""),
                "folderId": folder_id,
                "login": {
                    "username": data.get("username"),
                    "password": data.get("password"),
                    "totp": data.get("totp"),
                },
                "fields": [],
            }

            # Add URI if provided
            if data.get("uri"):
                item_data["login"]["uris"] = [{"uri": data["uri"]}]

            # Add custom fields
            for key, value in data.items():
                if key not in ["name", "username", "password", "uri", "notes", "totp"]:
                    item_data["fields"].append(
                        {
                            "name": key,
                            "value": value,
                            "type": 0,  # Text field
                        }
                    )

            # Create or update item
            try:
                # Try to create new item
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as f:
                    json.dump(item_data, f)
                    temp_file = f.name

                try:
                    await self._run_bw_command(["create", "item", temp_file])
                    logger.info(f"Created new Bitwarden item: {path}")
                finally:
                    os.unlink(temp_file)

            except SecretBackendError as e:
                if "already exists" in str(e).lower():
                    # Item exists, try to update
                    try:
                        # Get existing item
                        get_output = await self._run_bw_command(
                            ["get", "item", item_name]
                        )
                        existing_item = json.loads(get_output)

                        # Update with new data
                        existing_item.update(item_data)

                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=".json", delete=False
                        ) as f:
                            json.dump(existing_item, f)
                            temp_file = f.name

                        try:
                            await self._run_bw_command(
                                ["edit", "item", existing_item["id"], temp_file]
                            )
                            logger.info(f"Updated Bitwarden item: {path}")
                        finally:
                            os.unlink(temp_file)

                    except Exception as update_error:
                        raise SecretBackendError(
                            f"Failed to update existing item: {update_error}"
                        )
                else:
                    raise

            # Invalidate cache
            await self.cache.invalidate_path(path)

            # Return created/updated secret
            return await self.get_secret(path)

        except Exception as e:
            if isinstance(
                e, (SecretValidationError, SecretUnauthorizedError, SecretBackendError)
            ):
                raise
            raise SecretBackendError(f"Failed to store secret: {e}")

    async def list_secrets(self, prefix: str = "", limit: int = 100) -> List[str]:
        """
        List secrets under a given prefix.

        Args:
            prefix: Path prefix (folder name)
            limit: Maximum number of secrets to return

        Returns:
            List of secret paths
        """
        try:
            await self._ensure_authenticated()

            # Get items from Bitwarden
            list_cmd = ["list", "items"]
            if prefix:
                list_cmd.extend(["--folderid", prefix])  # Assume prefix is folder ID

            output = await self._run_bw_command(list_cmd)
            items = json.loads(output)

            # Convert to paths
            paths = []
            for item in items[:limit]:
                folder_name = "root"  # Default
                # Try to get folder name
                if item.get("folderId"):
                    try:
                        folder_output = await self._run_bw_command(
                            ["get", "folder", item["folderId"]]
                        )
                        folder_data = json.loads(folder_output)
                        folder_name = folder_data.get("name", "root")
                    except Exception:
                        pass

                path = f"{folder_name}/{item.get('name', item['id'])}"
                paths.append(path)

            logger.debug(f"Listed {len(paths)} secrets under prefix: {prefix}")
            return paths

        except Exception as e:
            if isinstance(e, (SecretUnauthorizedError, SecretBackendError)):
                raise
            raise SecretBackendError(f"Failed to list secrets: {e}")

    async def delete_secret(self, path: str, version: Optional[int] = None) -> None:
        """
        Delete a secret from Bitwarden.

        Args:
            path: Secret path
            version: Not supported (ignored)
        """
        try:
            await self._ensure_authenticated()

            item_path, field_name = self._path_to_item_id(path)

            if field_name:
                raise SecretBackendError(
                    "Deleting specific fields not supported via Bitwarden CLI"
                )

            # Delete item
            await self._run_bw_command(["delete", "item", item_path])

            # Invalidate cache
            await self.cache.invalidate_path(path)

            logger.info(f"Deleted secret from Bitwarden: {path}")

        except Exception as e:
            if isinstance(
                e, (SecretNotFoundError, SecretUnauthorizedError, SecretBackendError)
            ):
                raise
            raise SecretBackendError(f"Failed to delete secret: {e}")

    async def rotate_secret(self, path: str) -> str:
        """
        Rotate a secret value by generating a new random password.

        Args:
            path: Secret path

        Returns:
            New password value
        """
        import secrets
        import string

        # Generate a new random password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_password = "".join(secrets.choice(alphabet) for _ in range(16))

        try:
            # Get existing secret
            existing_secret = await self.get_secret(path)

            # Update password
            new_data = existing_secret.data.copy()
            new_data["password"] = new_password

            # Update the item
            await self.put_secret(path, new_data)

            logger.info(f"Rotated password for secret: {path}")
            return new_password

        except Exception as e:
            raise SecretBackendError(f"Failed to rotate secret: {e}")

    async def health(self) -> Dict[str, Any]:
        """
        Check Bitwarden adapter health.

        Returns:
            Dictionary with health status and metadata
        """
        try:
            await self._ensure_authenticated()

            # Get status
            status_output = await self._run_bw_command(["status"])
            status_data = json.loads(status_output)

            # Determine health
            user_email = status_data.get("userEmail")
            server_url = status_data.get("serverUrl")
            last_sync = status_data.get("lastSync")

            status = "healthy"
            if not user_email:
                status = "unhealthy"
            elif not last_sync:
                status = "degraded"

            return {
                "status": status,
                "authenticated": bool(user_email),
                "user_email": user_email,
                "server_url": server_url,
                "last_sync": last_sync,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def close(self) -> None:
        """Close resources."""
        await self.cache.stop()
