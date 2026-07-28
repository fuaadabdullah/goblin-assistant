from __future__ import annotations

from typing import Dict, Optional

from .base import Secret, SecretMetadata
from .cache import SecretCache


async def get_cached_secret(
    cache: SecretCache,
    path: str,
    version: Optional[int],
) -> Optional[Secret]:
    cached_secret = await cache.get_secret(path, version)
    if cached_secret is None:
        return None
    return Secret(
        path,
        cached_secret["data"],
        SecretMetadata(**cached_secret["metadata"]),
    )


async def cache_secret(
    cache: SecretCache,
    path: str,
    data: Dict[str, str],
    metadata: SecretMetadata,
    version: Optional[int],
) -> None:
    await cache.set_secret(
        path,
        {
            "data": data,
            "metadata": {
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at,
                "version": metadata.version,
                "custom_metadata": metadata.custom_metadata,
                "backend_specific": metadata.backend_specific,
            },
        },
        version,
    )
