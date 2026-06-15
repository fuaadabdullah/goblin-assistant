from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import structlog

from ...observability.context_snapshotter import (
    ContextSnapshot as ObsContextSnapshot,
)
from ...observability.context_snapshotter import (
    context_snapshotter,
)
from ..observability_models import ContextAssemblySnapshot
from .shared import compute_hash

logger = structlog.get_logger()


class ContextSnapshotFacet:
    def __init__(self, owner: Any):
        self._owner = owner

    def log_context_assembly_snapshot(
        self,
        request_id: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
        context_assembly: Dict[str, Any],
    ) -> None:
        try:
            context_text = context_assembly.get("context", "")
            metadata = {
                "conversation_id": conversation_id,
                "remaining_tokens": context_assembly.get("remaining_tokens", 0),
                "token_budget": context_assembly.get("token_budget", 0),
                "model_target": "unknown",
            }

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    context_snapshotter.create_snapshot(
                        correlation_id=request_id,
                        user_id=user_id,
                        context=context_text,
                        metadata=metadata,
                        assembly_time_ms=0.0,
                    )
                )
            except RuntimeError:
                pass

            snapshot = ObsContextSnapshot(
                snapshot_id=f"ctx_{int(datetime.utcnow().timestamp())}_{hash(compute_hash(context_text)) % 10000}",
                request_id=request_id,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                context_hash=compute_hash(context_text),
                context_layers=[{"type": "assembled_context", "content": context_text}],
                total_tokens=context_assembly.get("total_tokens_used", 0),
                remaining_tokens=context_assembly.get("remaining_tokens", 0),
                token_budget=context_assembly.get("token_budget", 0),
                model_target="unknown",
                redaction_applied=False,
                redaction_details={},
                assembly_time_ms=0.0,
                error=None,
            )
            context_snapshotter._snapshot_cache[request_id] = snapshot

            logger.info(
                "Context assembly snapshot logged",
                request_id=request_id,
            )

            self._owner.context_snapshots.append(
                ContextAssemblySnapshot(
                    request_id=request_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    context_hash=compute_hash(context_text),
                    redacted_snapshot={
                        "layers": context_assembly.get("layers", []),
                        "total_tokens": context_assembly.get("total_tokens_used", 0),
                        "remaining_tokens": context_assembly.get("remaining_tokens", 0),
                    },
                    total_token_usage=context_assembly.get("total_tokens_used", 0),
                    assembly_details={},
                    timestamp=datetime.utcnow().isoformat(),
                )
            )
        except Exception as e:
            logger.error("Failed to log context assembly snapshot", error=str(e))
