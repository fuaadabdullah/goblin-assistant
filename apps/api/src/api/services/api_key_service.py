"""Route-safe API key service facade."""

from __future__ import annotations

from typing import Optional

from api.storage.api_keys import create_api_key_store


async def store_provider_api_key(provider: str, key: str) -> None:
    store = create_api_key_store()
    await store.set(provider, key)


async def get_provider_api_key(provider: str) -> Optional[str]:
    store = create_api_key_store()
    return await store.get(provider)


async def delete_provider_api_key(provider: str) -> None:
    store = create_api_key_store()
    await store.delete(provider)
