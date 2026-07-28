"""Bitwarden item CRUD operations and cache integration."""

import json
import logging
import os
import tempfile
from typing import Any, Callable, Dict, Optional

from .base import SecretBackendError, SecretMetadata, SecretNotFoundError
from .cache import SecretCache

logger = logging.getLogger(__name__)


async def fetch_item_for_path(
    run_bw_fn: Callable,
    item_path: str,
    full_path: str,
) -> Dict[str, Any]:
    """
    Fetch a Bitwarden item by path, with fallback search.

    Args:
        run_bw_fn: Function to run bw commands
        item_path: Item path/name
        full_path: Full secret path (for error messages)

    Returns:
        Bitwarden item dictionary

    Raises:
        SecretNotFoundError: If item not found
    """
    try:
        output = await run_bw_fn(["get", "item", item_path])
        return json.loads(output)
    except SecretNotFoundError:
        # Try search fallback
        try:
            list_output = await run_bw_fn(["list", "items", "--search", item_path])
            items = json.loads(list_output)
            if items:
                return items[0]
        except Exception:
            pass
    raise SecretNotFoundError(f"Item not found: {full_path}")


async def resolve_folder_id(
    run_bw_fn: Callable,
    folder_name: Optional[str],
) -> Optional[str]:
    """
    Resolve folder name to Bitwarden folder ID.

    Args:
        run_bw_fn: Function to run bw commands
        folder_name: Folder name to resolve

    Returns:
        Folder ID or None if not found/no folder specified
    """
    if not folder_name:
        return None
    try:
        folders_output = await run_bw_fn(["list", "folders"])
        folders = json.loads(folders_output)
        for folder in folders:
            if folder.get("name") == folder_name:
                return folder["id"]
    except Exception:
        logger.warning("Could not find folder: %s", folder_name)
    return None


async def create_item(
    run_bw_fn: Callable,
    item_data: Dict[str, Any],
    path: str,
) -> None:
    """
    Create a new Bitwarden item.

    Args:
        run_bw_fn: Function to run bw commands
        item_data: Bitwarden item payload
        path: Secret path (for logging)

    Raises:
        SecretBackendError: If creation fails
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(item_data, f)
        temp_file = f.name
    try:
        await run_bw_fn(["create", "item", temp_file])
        logger.info("Created new Bitwarden item: %s", path)
    finally:
        os.unlink(temp_file)


async def update_existing_item(
    run_bw_fn: Callable,
    item_name: str,
    item_data: Dict[str, Any],
    path: str,
) -> None:
    """
    Update an existing Bitwarden item.

    Args:
        run_bw_fn: Function to run bw commands
        item_name: Item name/ID
        item_data: New item payload
        path: Secret path (for logging)

    Raises:
        SecretBackendError: If update fails
    """
    get_output = await run_bw_fn(["get", "item", item_name])
    existing_item = json.loads(get_output)
    existing_item.update(item_data)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(existing_item, f)
        temp_file = f.name
    try:
        await run_bw_fn(["edit", "item", existing_item["id"], temp_file])
        logger.info("Updated Bitwarden item: %s", path)
    finally:
        os.unlink(temp_file)


async def create_or_update_item(
    run_bw_fn: Callable,
    item_name: str,
    item_data: Dict[str, Any],
    path: str,
) -> None:
    """
    Create item if new, or update if already exists.

    Args:
        run_bw_fn: Function to run bw commands
        item_name: Item name
        item_data: Item payload
        path: Secret path (for logging)

    Raises:
        SecretBackendError: If both create and update fail
    """
    try:
        await create_item(run_bw_fn, item_data, path)
    except SecretBackendError as e:
        if "already exists" not in str(e).lower():
            raise
        try:
            await update_existing_item(run_bw_fn, item_name, item_data, path)
        except Exception as update_error:
            raise SecretBackendError(f"Failed to update existing item: {update_error}")


async def get_cached_secret(cache: SecretCache, path: str, version: Optional[int]):
    """
    Retrieve a secret from cache if available.

    Args:
        cache: SecretCache instance
        path: Secret path
        version: Secret version (optional)

    Returns:
        Secret object if cached, None otherwise
    """
    from .base import Secret

    cached_secret = await cache.get_secret(path, version)
    if cached_secret is None:
        return None
    logger.debug("Cache hit for secret: %s", path)
    return Secret(
        path,
        cached_secret["data"],
        SecretMetadata(**cached_secret["metadata"]),
    )


async def cache_secret(
    cache: SecretCache,
    path: str,
    secret,
    version: Optional[int],
) -> None:
    """
    Store a secret in cache.

    Args:
        cache: SecretCache instance
        path: Secret path
        secret: Secret object to cache
        version: Secret version (optional)
    """
    await cache.set_secret(
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
