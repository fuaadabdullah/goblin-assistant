from __future__ import annotations

import asyncio
from typing import Any


def build_snapshot_log_data(snapshot: Any) -> dict:
    return {
        "observability_event": True,
        "event_type": "context_snapshot",
        "snapshot": {
            "snapshot_id": snapshot.snapshot_id,
            "request_id": snapshot.request_id,
            "user_id": snapshot.user_id,
            "model_target": snapshot.model_target,
            "context_hash": snapshot.context_hash,
            "token_usage": {
                "total": snapshot.total_tokens,
                "remaining": snapshot.remaining_tokens,
                "budget": snapshot.token_budget,
                "utilization": (
                    round(snapshot.total_tokens / snapshot.token_budget * 100, 2)
                    if snapshot.token_budget > 0
                    else 0
                ),
            },
            "assembly_time_ms": snapshot.assembly_time_ms,
            "redaction": {
                "applied": snapshot.redaction_applied,
                "patterns": snapshot.redaction_details.get("patterns_applied", []),
                "items_redacted": snapshot.redaction_details.get("items_redacted", 0),
            },
            "error": snapshot.error,
        },
        "layers_summary": {
            "total_layers": len(snapshot.context_layers),
            "layer_types": [layer.get("name", "unknown") for layer in snapshot.context_layers],
            "avg_layer_tokens": round(
                sum(layer.get("tokens", 0) for layer in snapshot.context_layers)
                / max(1, len(snapshot.context_layers)),
                2,
            ),
        },
    }


def log_snapshot_structured(logger: Any, snapshot: Any) -> None:
    log_data = build_snapshot_log_data(snapshot)
    if snapshot.error:
        logger.error("CONTEXT: Assembly error", extra={"context": log_data})
    elif snapshot.redaction_details.get("items_redacted", 0) > 0:
        logger.warning("CONTEXT: Sensitive data redacted", extra={"context": log_data})
    else:
        logger.info("CONTEXT: Snapshot captured", extra={"context": log_data})


async def log_snapshot_to_file(config: dict, logger: Any, snapshot: Any) -> None:
    try:
        log_file = config.get("observability", {}).get("snapshot_log_file", "snapshots.log")

        def _append() -> None:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(snapshot.to_json() + "\n")

        await asyncio.to_thread(_append)
    except Exception as e:
        logger.error("Failed to log snapshot to file:", error=str(e))
