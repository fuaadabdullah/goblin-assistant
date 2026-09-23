"""
Bitwarden Secrets Manager adapter using the official bitwarden-sdk.

Provides an async interface to Bitwarden Secrets Manager (organization → projects
→ secrets) via the official `bitwarden_sdk` bindings, replacing the previous
subprocess-based `bw` CLI integration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import string
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from bitwarden_sdk import BitwardenClient, ClientSettings

from .base import (
    Secret,
    SecretAdapter,
    SecretBackendError,
    SecretMetadata,
    SecretNotFoundError,
    SecretUnauthorizedError,
    SecretValidationError,
)
from .cache import SecretCache

logger = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://api.bitwarden.com"
_DEFAULT_IDENTITY_URL = "https://identity.bitwarden.com"


def _coerce_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _data_to_value_note(data: Dict[str, str]) -> tuple[str, Optional[str]]:
    """Map a Secret.data dict onto a Secrets Manager value + note."""
    if not data:
        return "", None
    if "value" in data:
        value = str(data["value"])
        extra = {key: val for key, val in data.items() if key != "value"}
        return value, json.dumps(extra) if extra else None
    # No canonical "value" key: serialize the whole dict as the secret value.
    return json.dumps(data), None


def _value_note_to_data(value: str, note: Optional[str]) -> Dict[str, str]:
    data: Dict[str, str] = {"value": value or ""}
    if not note:
        return data
    try:
        extra = json.loads(note)
    except (ValueError, TypeError):
        extra = None
    if isinstance(extra, dict):
        for key, val in extra.items():
            data[str(key)] = str(val)
    else:
        data["notes"] = note
    return data


class BitwardenAdapter(SecretAdapter):
    """Bitwarden Secrets Manager adapter backed by the official SDK."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        organization_id: Optional[str] = None,
        project_id: Optional[str] = None,
        api_url: Optional[str] = None,
        identity_url: Optional[str] = None,
        cache_ttl: int = 300,
        cache_size: int = 1000,
    ) -> None:
        self.access_token = access_token or os.getenv("BITWARDEN_ACCESS_TOKEN", "")
        self.organization_id = organization_id or os.getenv("BITWARDEN_ORGANIZATION_ID", "")
        self.project_id = project_id or os.getenv("BITWARDEN_PROJECT_ID", "")
        self.api_url = api_url or os.getenv("BITWARDEN_API_URL", _DEFAULT_API_URL)
        self.identity_url = identity_url or os.getenv(
            "BITWARDEN_IDENTITY_URL", _DEFAULT_IDENTITY_URL
        )
        self.cache = SecretCache(max_size=cache_size, default_ttl=cache_ttl)
        self._client: Optional[BitwardenClient] = None

    def _build_client(self) -> BitwardenClient:
        if not self.access_token:
            raise SecretUnauthorizedError("BITWARDEN_ACCESS_TOKEN is required")
        if not self.organization_id:
            raise SecretUnauthorizedError("BITWARDEN_ORGANIZATION_ID is required")

        client = BitwardenClient(
            settings=ClientSettings(api_url=self.api_url, identity_url=self.identity_url)
        )
        login = client.auth.login_access_token(self.access_token)
        if not login.success:
            raise SecretUnauthorizedError(
                f"Bitwarden access token login failed: {login.error_message}"
            )
        return client

    async def _get_client(self) -> BitwardenClient:
        if self._client is None:
            self._client = await asyncio.to_thread(self._build_client)
        return self._client

    def _find_secret_id(self, client: BitwardenClient, key: str) -> Optional[str]:
        listing = client.secrets().list(self.organization_id)
        if not listing.success:
            raise SecretBackendError(listing.error_message or "failed to list secrets")
        for identifier in listing.data.data:
            if identifier.key == key:
                return identifier.id
        return None

    def _secret_response_to_secret(self, path: str, resp: Any) -> Secret:
        metadata = SecretMetadata(
            created_at=_coerce_dt(getattr(resp, "creation_date", None)),
            updated_at=_coerce_dt(getattr(resp, "revision_date", None)),
            custom_metadata={
                "organization_id": getattr(resp, "organization_id", None),
                "project_id": getattr(resp, "project_id", None),
            },
            backend_specific={
                "bitwarden_secret_id": getattr(resp, "id", None),
                "bitwarden_project_id": getattr(resp, "project_id", None),
            },
        )
        return Secret(
            path=path,
            data=_value_note_to_data(
                getattr(resp, "value", "") or "",
                getattr(resp, "note", None),
            ),
            metadata=metadata,
        )

    async def get_secret(self, path: str, version: Optional[int] = None) -> Secret:
        client = await self._get_client()

        def _op() -> Secret:
            secret_id = self._find_secret_id(client, path)
            if secret_id is None:
                raise SecretNotFoundError(path)
            resp = client.secrets().get(secret_id)
            if not resp.success:
                raise SecretBackendError(resp.error_message or "failed to get secret")
            return self._secret_response_to_secret(path, resp.data)

        return await asyncio.to_thread(_op)

    async def put_secret(
        self,
        path: str,
        data: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        version: Optional[int] = None,
    ) -> Secret:
        if not data:
            raise SecretValidationError("Secret data cannot be empty")

        client = await self._get_client()
        value, note = _data_to_value_note(data)
        project_ids = [uuid.UUID(self.project_id)] if self.project_id else None

        def _op() -> Secret:
            secret_id = self._find_secret_id(client, path)
            if secret_id is None:
                resp = client.secrets().create(
                    uuid.UUID(self.organization_id), path, value, note, project_ids
                )
            else:
                resp = client.secrets().update(
                    self.organization_id, secret_id, path, value, note, project_ids
                )
            if not resp.success:
                raise SecretBackendError(resp.error_message or "failed to store secret")
            return self._secret_response_to_secret(path, resp.data)

        secret = await asyncio.to_thread(_op)
        await self.cache.invalidate_path(path)
        return secret

    async def list_secrets(self, prefix: str = "", limit: int = 100) -> List[str]:
        client = await self._get_client()

        def _op() -> List[str]:
            listing = client.secrets().list(self.organization_id)
            if not listing.success:
                raise SecretBackendError(listing.error_message or "failed to list secrets")
            keys = [identifier.key for identifier in listing.data.data]
            if prefix:
                keys = [key for key in keys if key.startswith(prefix)]
            return keys[:limit]

        return await asyncio.to_thread(_op)

    async def delete_secret(self, path: str, version: Optional[int] = None) -> None:
        client = await self._get_client()

        def _op() -> None:
            secret_id = self._find_secret_id(client, path)
            if secret_id is None:
                raise SecretNotFoundError(path)
            resp = client.secrets().delete([secret_id])
            if not resp.success:
                raise SecretBackendError(resp.error_message or "failed to delete secret")

        await asyncio.to_thread(_op)
        await self.cache.invalidate_path(path)

    async def rotate_secret(self, path: str) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_value = "".join(secrets.choice(alphabet) for _ in range(16))
        existing = await self.get_secret(path)
        new_data = dict(existing.data)
        new_data["value"] = new_value
        await self.put_secret(path, new_data)
        logger.info("Rotated secret: %s", path)
        return new_value

    async def health(self) -> Dict[str, Any]:
        try:
            client = await self._get_client()

            def _op() -> bool:
                listing = client.projects().list(self.organization_id)
                return bool(listing.success)

            ok = await asyncio.to_thread(_op)
            return {
                "status": "healthy" if ok else "unhealthy",
                "authenticated": True,
                "organization_id": self.organization_id,
                "project_id": self.project_id or None,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("Health check failed: %s", exc)
            return {
                "status": "unhealthy",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def close(self) -> None:
        self._client = None
        await self.cache.stop()
