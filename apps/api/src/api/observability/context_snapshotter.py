"""
Context Assembly Snapshot System.

Compatibility facade over the dedicated context_snapshotter helper modules.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from ..config.system_config import get_system_config
from .context_snapshotter_logging import log_snapshot_structured, log_snapshot_to_file
from .context_snapshotter_redaction import (
    calculate_context_hash,
    extract_context_content,
    redact_context_layers,
    redact_text,
)
from .context_snapshotter_reports import (
    build_context_assembly_stats,
    build_context_health_report,
    build_replay_context,
    filter_snapshots,
    generate_health_recommendations,
    get_layer_type_distribution,
    search_snapshot_cache,
    snapshots_to_history,
)

logger = structlog.get_logger()


@dataclass
class ContextSnapshot:
    """Redacted snapshot of assembled context."""

    snapshot_id: str
    request_id: str
    user_id: Optional[str]
    timestamp: datetime
    context_hash: str
    context_layers: List[Dict[str, Any]]
    total_tokens: int
    remaining_tokens: int
    token_budget: int
    model_target: str
    redaction_applied: bool
    redaction_details: Dict[str, Any]
    assembly_time_ms: float
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)


class ContextSnapshotter:
    """System for capturing and managing context assembly snapshots."""

    def __init__(self):
        self.config = get_system_config()
        self._snapshot_cache: Dict[str, ContextSnapshot] = {}
        self._redaction_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b\d{16}\b",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            r"\b\d{3}-\d{3}-\d{4}\b",
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        ]

    async def capture_context_snapshot(
        self,
        request_id: str,
        user_id: Optional[str],
        context_layers: List[Dict[str, Any]],
        total_tokens: int,
        remaining_tokens: int,
        token_budget: int,
        model_target: str,
        assembly_time_ms: float,
        error: Optional[str] = None,
    ) -> ContextSnapshot:
        context_content = self._extract_context_content(context_layers)
        context_hash = self._calculate_context_hash(context_content)
        redacted_layers, redaction_details = self._redact_context_layers(context_layers)

        snapshot = ContextSnapshot(
            snapshot_id=f"ctx_{int(datetime.utcnow().timestamp())}_{hash(context_hash) % 10000}",
            request_id=request_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            context_hash=context_hash,
            context_layers=redacted_layers,
            total_tokens=total_tokens,
            remaining_tokens=remaining_tokens,
            token_budget=token_budget,
            model_target=model_target,
            redaction_applied=True,
            redaction_details=redaction_details,
            assembly_time_ms=assembly_time_ms,
            error=error,
        )

        self._snapshot_cache[request_id] = snapshot
        self._log_snapshot_structured(snapshot)

        if self.config.get("observability", {}).get("log_snapshots_to_file", False):
            await self._log_to_file(snapshot)

        return snapshot

    async def create_snapshot(self, **kwargs):
        context = kwargs.get("context", "")
        if isinstance(context, str):
            context_layers = [{"type": "assembled_context", "content": context}]
        else:
            context_layers = context if isinstance(context, list) else []

        snapshot = await self.capture_context_snapshot(
            request_id=kwargs.get("correlation_id") or f"req_{int(time.time())}",
            user_id=kwargs.get("user_id"),
            context_layers=context_layers,
            total_tokens=0,
            remaining_tokens=kwargs.get("metadata", {}).get("remaining_tokens", 8000),
            token_budget=kwargs.get("metadata", {}).get("token_budget", 8000),
            model_target=kwargs.get("metadata", {}).get("model_target", "unknown"),
            assembly_time_ms=kwargs.get("assembly_time_ms", 0.0),
            error=kwargs.get("error"),
        )
        return getattr(snapshot, "snapshot_id", None)

    def _extract_context_content(self, context_layers: List[Dict[str, Any]]) -> str:
        return extract_context_content(context_layers)

    def _calculate_context_hash(self, content: str) -> str:
        return calculate_context_hash(content)

    def _redact_context_layers(
        self, context_layers: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        return redact_context_layers(context_layers, self._redaction_patterns)

    def _redact_text(self, text: str):
        return redact_text(text, self._redaction_patterns)

    def _log_snapshot_structured(self, snapshot: ContextSnapshot):
        log_snapshot_structured(logger, snapshot)

    async def _log_to_file(self, snapshot: ContextSnapshot):
        await log_snapshot_to_file(self.config, logger, snapshot)

    async def get_context_snapshot(self, request_id: str) -> Optional[Dict[str, Any]]:
        if request_id in self._snapshot_cache:
            return self._snapshot_cache[request_id].to_dict()
        return None

    async def get_context_history(
        self,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        snapshots = filter_snapshots(self._snapshot_cache, user_id=user_id, model=model)
        return snapshots_to_history(snapshots, limit)

    async def get_context_assembly_stats(
        self,
        user_id: Optional[str] = None,
        time_window_hours: int = 24,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        relevant_snapshots = filter_snapshots(
            self._snapshot_cache,
            user_id=user_id,
            model=model,
            time_window_hours=time_window_hours,
        )
        return build_context_assembly_stats(
            relevant_snapshots,
            user_id=user_id,
            time_window_hours=time_window_hours,
            model=model,
        )

    def _get_layer_type_distribution(self, snapshots: List[ContextSnapshot]) -> Dict[str, int]:
        return get_layer_type_distribution(snapshots)

    async def get_context_health_report(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        user_snapshots = filter_snapshots(self._snapshot_cache, user_id=user_id)
        return build_context_health_report(user_snapshots, user_id=user_id)

    def _generate_health_recommendations(
        self,
        avg_utilization: float,
        avg_assembly_time: float,
        redaction_rate: float,
        error_rate: float,
        layer_consistency: float,
    ) -> List[str]:
        return generate_health_recommendations(
            avg_utilization,
            avg_assembly_time,
            redaction_rate,
            error_rate,
            layer_consistency,
        )

    async def search_snapshots(
        self,
        query: str,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return search_snapshot_cache(
            self._snapshot_cache,
            query=query,
            user_id=user_id,
            model=model,
            start_time=start_time,
            end_time=end_time,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
        )

    async def replay_context(self, request_id: str) -> Optional[Dict[str, Any]]:
        snapshot = await self.get_context_snapshot(request_id)
        if not snapshot:
            return None
        return build_replay_context(snapshot, request_id)


context_snapshotter = ContextSnapshotter()


async def capture_context_snapshot(
    request_id: str,
    user_id: Optional[str],
    context_layers: List[Dict[str, Any]],
    total_tokens: int,
    remaining_tokens: int,
    token_budget: int,
    model_target: str,
    assembly_time_ms: float,
    error: Optional[str] = None,
) -> ContextSnapshot:
    return await context_snapshotter.capture_context_snapshot(
        request_id=request_id,
        user_id=user_id,
        context_layers=context_layers,
        total_tokens=total_tokens,
        remaining_tokens=remaining_tokens,
        token_budget=token_budget,
        model_target=model_target,
        assembly_time_ms=assembly_time_ms,
        error=error,
    )
