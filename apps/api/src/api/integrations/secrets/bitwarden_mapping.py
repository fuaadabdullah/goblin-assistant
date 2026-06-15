"""Bitwarden item ↔ Secret data mapping and serialization."""

from datetime import datetime
from typing import Any, Dict, Optional

from .base import Secret, SecretMetadata


def parse_bw_time(time_str: Optional[str]) -> Optional[datetime]:
    """
    Parse Bitwarden timestamp string to datetime object.

    Args:
        time_str: ISO 8601 timestamp string from Bitwarden

    Returns:
        Parsed datetime or None if parsing fails
    """
    if not time_str:
        return None
    try:
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except Exception:
        return None


def path_to_item_id(path: str) -> tuple[str, Optional[str]]:
    """
    Convert secret path to Bitwarden item ID and optional field name.

    Path format: "folder/item" or "folder/item.field"

    Args:
        path: Secret path

    Returns:
        (item_path, field_name) tuple
    """
    parts = path.split(".")
    item_path = parts[0]
    field_name = parts[1] if len(parts) > 1 else None
    return item_path, field_name


def item_to_secret(
    item: Dict[str, Any],
    field_name: Optional[str] = None,
) -> Secret:
    """
    Convert Bitwarden item to Secret object.

    Args:
        item: Bitwarden item dictionary
        field_name: Optional specific field name to extract

    Returns:
        Secret object with data and metadata
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
            "uri": (
                item.get("login", {}).get("uris", [{}])[0].get("uri", "")
                if item.get("login", {}).get("uris")
                else ""
            ),
            "notes": item.get("notes", ""),
            "totp": item.get("login", {}).get("totp", ""),
        }
        # Add custom fields
        for field in item.get("fields", []):
            secret_data[field["name"]] = field.get("value", "")

    # Create metadata
    metadata = SecretMetadata(
        created_at=parse_bw_time(item.get("creationDate")),
        updated_at=parse_bw_time(item.get("revisionDate")),
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


def build_item_data(
    item_name: str,
    folder_id: Optional[str],
    data: Dict[str, str],
) -> Dict[str, Any]:
    """
    Build Bitwarden item payload from secret data.

    Args:
        item_name: Name of the secret/item
        folder_id: Bitwarden folder ID (optional)
        data: Secret data dictionary

    Returns:
        Bitwarden item JSON structure
    """
    item_data = {
        "type": 1,
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
    if data.get("uri"):
        item_data["login"]["uris"] = [{"uri": data["uri"]}]

    # Add custom fields
    for key, value in data.items():
        if key not in ["name", "username", "password", "uri", "notes", "totp"]:
            item_data["fields"].append({"name": key, "value": value, "type": 0})

    return item_data
