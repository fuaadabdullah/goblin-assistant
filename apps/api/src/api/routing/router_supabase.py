"""Fire-and-forget Supabase mirroring and restore for routing stats."""

from __future__ import annotations

import asyncio
import time
from typing import Dict

import structlog

from .registry_store import ProviderStats

logger = structlog.get_logger()


def schedule_mirror(
    stats: Dict[str, ProviderStats], hourly_spend: Dict[str, Dict[str, float]]
) -> None:
    """Schedule an async Supabase upsert from any sync context (best-effort)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_async_mirror(stats, hourly_spend))
    except RuntimeError:
        pass  # no running loop (e.g. atexit) — skip


async def _async_mirror(
    stats: Dict[str, ProviderStats],
    hourly_spend: Dict[str, Dict[str, float]],
) -> None:
    try:
        from ..providers.supabase_events import (  # noqa: PLC0415
            _ENABLED,
            _HEADERS,
            _REST,
            _get_client,
        )

        if not _ENABLED:
            return
        now = time.time()
        stat_rows = [
            {
                "provider_id": s.provider_id,
                "ewma_latency_ms": s.ewma_latency_ms,
                "ewma_alpha": s.ewma_alpha,
                "success_count": s.success_count,
                "failure_count": s.failure_count,
                "total_cost_usd": s.total_cost_usd,
                "last_used": s.last_used,
                "updated_at": now,
            }
            for s in stats.values()
        ]
        spend_rows = [
            {
                "hour_bucket": hb,
                "provider_id": pid,
                "spend_usd": spend,
                "updated_at": now,
            }
            for hb, provider_spend in hourly_spend.items()
            for pid, spend in provider_spend.items()
        ]
        client = _get_client()
        prefer = "resolution=merge-duplicates,return=minimal"
        if stat_rows:
            await client.post(
                f"{_REST}/provider_routing_stats",
                headers={**_HEADERS, "Prefer": prefer},
                json=stat_rows,
            )
        if spend_rows:
            await client.post(
                f"{_REST}/provider_hourly_spend",
                headers={**_HEADERS, "Prefer": prefer},
                json=spend_rows,
            )
    except Exception as exc:
        logger.debug("routing_registry_supabase_mirror_failed", error=str(exc))


async def restore_from_supabase(
    stats: Dict[str, ProviderStats],
    hourly_spend: Dict[str, Dict[str, float]],
) -> None:
    """Restore in-memory stats from Supabase when SQLite is empty.

    Mutates ``stats`` and ``hourly_spend`` in-place. Called once at startup
    via lifespan. No-op if ``stats`` already has data (SQLite survived the deploy).
    """
    if stats:
        return
    try:
        from ..providers.supabase_events import (  # noqa: PLC0415
            _ENABLED,
            _HEADERS,
            _REST,
            _get_client,
        )

        if not _ENABLED:
            return
        client = _get_client()
        stats_resp = await client.get(
            f"{_REST}/provider_routing_stats",
            headers=_HEADERS,
            params={
                "select": (
                    "provider_id,ewma_latency_ms,ewma_alpha,"
                    "success_count,failure_count,total_cost_usd,last_used"
                )
            },
        )
        spend_resp = await client.get(
            f"{_REST}/provider_hourly_spend",
            headers=_HEADERS,
            params={"select": "hour_bucket,provider_id,spend_usd"},
        )
        stat_rows = stats_resp.json()
        spend_rows = spend_resp.json()

        if isinstance(stat_rows, list):
            for row in stat_rows:
                if not isinstance(row, dict) or "provider_id" not in row:
                    continue
                stats[row["provider_id"]] = ProviderStats(
                    provider_id=row["provider_id"],
                    ewma_latency_ms=float(row.get("ewma_latency_ms", 5000.0)),
                    ewma_alpha=float(row.get("ewma_alpha", 0.2)),
                    success_count=int(row.get("success_count", 0)),
                    failure_count=int(row.get("failure_count", 0)),
                    total_cost_usd=float(row.get("total_cost_usd", 0.0)),
                    last_used=float(row.get("last_used", time.time())),
                )

        if isinstance(spend_rows, list):
            for row in spend_rows:
                if not isinstance(row, dict):
                    continue
                hourly_spend.setdefault(str(row["hour_bucket"]), {})[str(row["provider_id"])] = (
                    float(row["spend_usd"])
                )

        if stats:
            logger.info("routing_registry_restored_from_supabase", providers=len(stats))
    except Exception as exc:
        logger.warning("routing_registry_supabase_restore_failed", error=str(exc))
