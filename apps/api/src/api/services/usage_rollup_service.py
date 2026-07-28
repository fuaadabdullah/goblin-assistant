"""Route-safe usage rollup queries for observability endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.storage.usage_events import usage_event_store


async def get_model_usage_rollup(
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    return await usage_event_store.get_model_rollup(provider=provider, model=model, limit=limit)
