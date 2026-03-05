"""
Context Assembly Snapshot System
Captures redacted snapshots of context before sending to models for debugging and replay
"""

import json
import hashlib
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog

from ..config.system_config import get_system_config

logger = structlog.get_logger()


@dataclass
class ContextSnapshot:
    """Redacted snapshot of assembled context"""

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
        """Convert to dictionary for logging"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string for structured logging"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class ContextSnapshotter:
    """System for capturing and managing context assembly snapshots"""

    def __init__(self):
        self.config = get_system_config()
        self._snapshot_cache = {}  # Cache recent snapshots for debugging
        self._redaction_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{16}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}-\d{3}-\d{4}\b",  # Phone
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP address
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
        """Capture a redacted snapshot of assembled context"""

        # Calculate context hash
        context_content = self._extract_context_content(context_layers)
        context_hash = self._calculate_context_hash(context_content)

        # Apply redaction
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

        # Store in cache for debugging
        self._snapshot_cache[request_id] = snapshot

        # Log with structured format
        self._log_snapshot_structured(snapshot)

        # Log to file if configured
        if self.config.get("observability", {}).get("log_snapshots_to_file", False):
            await self._log_to_file(snapshot)

        return snapshot

    async def create_snapshot(self, **kwargs):
        """Wrapper for capture_context_snapshot to match service call."""
        # Service passes context as a string or list. Ensure it's context_layers (list of dicts).
        context = kwargs.get("context", "")
        if isinstance(context, str):
            context_layers = [{"type": "assembled_context", "content": context}]
        else:
            context_layers = context if isinstance(context, list) else []

        # Map arguments from ContextAssemblyService to capture_context_snapshot
        return await self.capture_context_snapshot(
            request_id=kwargs.get("correlation_id") or f"req_{int(time.time())}",
            user_id=kwargs.get("user_id"),
            context_layers=context_layers,
            total_tokens=0,  # Calculated internally if needed
            remaining_tokens=kwargs.get("metadata", {}).get("remaining_tokens", 8000),
            token_budget=kwargs.get("metadata", {}).get("token_budget", 8000),
            model_target=kwargs.get("metadata", {}).get("model_target", "unknown"),
            assembly_time_ms=kwargs.get("assembly_time_ms", 0.0),
            error=kwargs.get("error"),
        )

    def _extract_context_content(self, context_layers: List[Dict[str, Any]]) -> str:
        """Extract text content from context layers for hashing"""
        content_parts = []
        for layer in context_layers:
            if "content" in layer:
                content_parts.append(layer["content"])
            elif "text" in layer:
                content_parts.append(layer["text"])
        return "\n".join(content_parts)

    def _calculate_context_hash(self, content: str) -> str:
        """Calculate hash of context content for deduplication and comparison"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _redact_context_layers(
        self, context_layers: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Apply redaction to context layers to protect user secrets"""

        redaction_details = {
            "patterns_applied": [],
            "items_redacted": 0,
            "layers_processed": len(context_layers),
        }

        redacted_layers = []

        for layer in context_layers:
            redacted_layer = layer.copy()

            if "content" in redacted_layer:
                original_content = redacted_layer["content"]
                redacted_content, patterns_found = self._redact_text(original_content)
                redacted_layer["content"] = redacted_content

                if patterns_found:
                    redaction_details["patterns_applied"].extend(patterns_found)
                    redaction_details["items_redacted"] += len(patterns_found)

            redacted_layers.append(redacted_layer)

        return redacted_layers, redaction_details

    def _redact_text(self, text: str) -> Tuple[str, List[str]]:
        """Redact sensitive information from text"""

        redacted_text = text
        patterns_found = []

        # SSN redaction
        ssn_pattern = r"\b(\d{3})-(\d{2})-(\d{4})\b"
        if re.search(ssn_pattern, text):
            redacted_text = re.sub(ssn_pattern, r"XXX-XX-XXXX", redacted_text)
            patterns_found.append("ssn")

        # Credit card redaction
        cc_pattern = r"\b(\d{4})[\s-](\d{4})[\s-](\d{4})[\s-](\d{4})\b"
        if re.search(cc_pattern, text):
            redacted_text = re.sub(cc_pattern, r"XXXX-XXXX-XXXX-XXXX", redacted_text)
            patterns_found.append("credit_card")

        # Email redaction
        email_pattern = r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b"
        if re.search(email_pattern, text):
            redacted_text = re.sub(email_pattern, r"[REDACTED_EMAIL]", redacted_text)
            patterns_found.append("email")

        # Phone number redaction
        phone_pattern = r"\b(\d{3})-(\d{3})-(\d{4})\b"
        if re.search(phone_pattern, text):
            redacted_text = re.sub(phone_pattern, r"XXX-XXX-XXXX", redacted_text)
            patterns_found.append("phone")

        # IP address redaction
        ip_pattern = r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b"
        if re.search(ip_pattern, text):
            redacted_text = re.sub(ip_pattern, r"XXX.XXX.XXX.XXX", redacted_text)
            patterns_found.append("ip_address")

        # Custom redaction patterns from config
        custom_patterns = self.config.get("observability", {}).get(
            "redaction_patterns", []
        )
        for pattern in custom_patterns:
            if re.search(pattern, text):
                redacted_text = re.sub(pattern, "[REDACTED]", redacted_text)
                patterns_found.append("custom_pattern")

        return redacted_text, patterns_found

    def _log_snapshot_structured(self, snapshot: ContextSnapshot):
        """Log context snapshot with structured format for observability"""

        # Create structured log entry
        log_data = {
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
                    "utilization": round(
                        snapshot.total_tokens / snapshot.token_budget * 100, 2
                    )
                    if snapshot.token_budget > 0
                    else 0,
                },
                "assembly_time_ms": snapshot.assembly_time_ms,
                "redaction": {
                    "applied": snapshot.redaction_applied,
                    "patterns": snapshot.redaction_details.get("patterns_applied", []),
                    "items_redacted": snapshot.redaction_details.get(
                        "items_redacted", 0
                    ),
                },
                "error": snapshot.error,
            },
            "layers_summary": {
                "total_layers": len(snapshot.context_layers),
                "layer_types": [
                    layer.get("name", "unknown") for layer in snapshot.context_layers
                ],
                "avg_layer_tokens": round(
                    sum(layer.get("tokens", 0) for layer in snapshot.context_layers)
                    / max(1, len(snapshot.context_layers)),
                    2,
                ),
            },
        }

        # Log based on snapshot outcome
        if snapshot.error:
            logger.error("CONTEXT: Assembly error", extra={"context": log_data})
        elif snapshot.redaction_details.get("items_redacted", 0) > 0:
            logger.warning(
                "CONTEXT: Sensitive data redacted", extra={"context": log_data}
            )
        else:
            logger.info("CONTEXT: Snapshot captured", extra={"context": log_data})

    async def _log_to_file(self, snapshot: ContextSnapshot):
        """Log context snapshot to file for persistent storage"""
        try:
            log_file = self.config.get("observability", {}).get(
                "snapshot_log_file", "snapshots.log"
            )

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(snapshot.to_json() + "\n")

        except Exception as e:
            logger.error(f"Failed to log snapshot to file: {e}")

    async def get_context_snapshot(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific context snapshot by request ID"""
        if request_id in self._snapshot_cache:
            return self._snapshot_cache[request_id].to_dict()
        return None

    async def get_context_history(
        self,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get context assembly history with filtering"""

        # Filter snapshots by user and model
        snapshots = []
        for snapshot in self._snapshot_cache.values():
            if user_id and snapshot.user_id != user_id:
                continue
            if model and snapshot.model_target != model:
                continue
            snapshots.append(snapshot.to_dict())

        # Sort by timestamp and limit
        snapshots.sort(key=lambda x: x["timestamp"], reverse=True)
        return snapshots[:limit]

    async def get_context_assembly_stats(
        self,
        user_id: Optional[str] = None,
        time_window_hours: int = 24,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get context assembly statistics for monitoring"""

        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)

        # Filter snapshots by time window, user, and model
        relevant_snapshots = []
        for snapshot in self._snapshot_cache.values():
            if snapshot.timestamp >= cutoff_time:
                if user_id is None or snapshot.user_id == user_id:
                    if model is None or snapshot.model_target == model:
                        relevant_snapshots.append(snapshot)

        if not relevant_snapshots:
            return {
                "total_assemblies": 0,
                "time_window_hours": time_window_hours,
                "user_id": user_id,
                "model": model,
            }

        # Calculate statistics
        total = len(relevant_snapshots)

        # Token usage statistics
        token_stats = {
            "avg_tokens_used": round(
                sum(s.total_tokens for s in relevant_snapshots) / total, 2
            ),
            "max_tokens_used": max(s.total_tokens for s in relevant_snapshots),
            "min_tokens_used": min(s.total_tokens for s in relevant_snapshots),
            "avg_token_utilization": round(
                sum(s.total_tokens / s.token_budget * 100 for s in relevant_snapshots)
                / total,
                2,
            ),
        }

        # Assembly performance statistics
        assembly_stats = {
            "avg_assembly_time": round(
                sum(s.assembly_time_ms for s in relevant_snapshots) / total, 2
            ),
            "max_assembly_time": max(s.assembly_time_ms for s in relevant_snapshots),
            "min_assembly_time": min(s.assembly_time_ms for s in relevant_snapshots),
        }

        # Redaction statistics
        redaction_stats = {
            "total_redactions": sum(
                s.redaction_details.get("items_redacted", 0) for s in relevant_snapshots
            ),
            "snapshots_with_redaction": sum(
                1
                for s in relevant_snapshots
                if s.redaction_details.get("items_redacted", 0) > 0
            ),
            "redaction_rate": round(
                sum(
                    1
                    for s in relevant_snapshots
                    if s.redaction_details.get("items_redacted", 0) > 0
                )
                / total
                * 100,
                2,
            ),
        }

        # Layer statistics
        layer_stats = {
            "avg_layers_per_assembly": round(
                sum(len(s.context_layers) for s in relevant_snapshots) / total, 2
            ),
            "layer_types": self._get_layer_type_distribution(relevant_snapshots),
        }

        # Error rate
        error_count = sum(1 for s in relevant_snapshots if s.error)
        error_rate = round(error_count / total * 100, 2)

        return {
            "total_assemblies": total,
            "time_window_hours": time_window_hours,
            "user_id": user_id,
            "model": model,
            "token_stats": token_stats,
            "assembly_stats": assembly_stats,
            "redaction_stats": redaction_stats,
            "layer_stats": layer_stats,
            "error_rate": error_rate,
        }

    def _get_layer_type_distribution(
        self, snapshots: List[ContextSnapshot]
    ) -> Dict[str, int]:
        """Get distribution of layer types across snapshots"""
        layer_types = {}
        for snapshot in snapshots:
            for layer in snapshot.context_layers:
                layer_type = layer.get("name", "unknown")
                layer_types[layer_type] = layer_types.get(layer_type, 0) + 1
        return layer_types

    async def get_context_health_report(
        self, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive context assembly health report"""

        # Get all snapshots for user
        user_snapshots = []
        for snapshot in self._snapshot_cache.values():
            if user_id is None or snapshot.user_id == user_id:
                user_snapshots.append(snapshot)

        if not user_snapshots:
            return {
                "user_id": user_id,
                "status": "no_data",
                "message": "No context snapshots found",
            }

        # Calculate health metrics
        total_snapshots = len(user_snapshots)

        # Token utilization analysis
        token_utilization = [
            s.total_tokens / s.token_budget * 100 for s in user_snapshots
        ]
        avg_utilization = sum(token_utilization) / len(token_utilization)

        # Assembly performance analysis
        assembly_times = [s.assembly_time_ms for s in user_snapshots]
        avg_assembly_time = sum(assembly_times) / len(assembly_times)

        # Redaction analysis
        total_redactions = sum(
            s.redaction_details.get("items_redacted", 0) for s in user_snapshots
        )
        redaction_rate = (
            total_redactions
            / max(1, sum(len(s.context_layers) for s in user_snapshots))
            * 100
        )

        # Error analysis
        error_count = sum(1 for s in user_snapshots if s.error)
        error_rate = error_count / total_snapshots * 100

        # Layer consistency analysis
        layer_counts = [len(s.context_layers) for s in user_snapshots]
        layer_consistency = (
            100
            - (max(layer_counts) - min(layer_counts)) / max(1, sum(layer_counts)) * 100
        )

        # Determine health status
        if error_rate > 10:
            health_status = "critical"
        elif avg_assembly_time > 1000:  # > 1 second
            health_status = "warning"
        elif avg_utilization > 95:
            health_status = "warning"
        elif redaction_rate > 20:
            health_status = "warning"
        elif layer_consistency < 70:
            health_status = "warning"
        else:
            health_status = "healthy"

        return {
            "user_id": user_id,
            "health_status": health_status,
            "metrics": {
                "total_assemblies": total_snapshots,
                "avg_token_utilization": round(avg_utilization, 2),
                "avg_assembly_time_ms": round(avg_assembly_time, 2),
                "redaction_rate": round(redaction_rate, 2),
                "error_rate": round(error_rate, 2),
                "layer_consistency": round(layer_consistency, 2),
                "assembly_performance": {
                    "min_time_ms": min(assembly_times),
                    "max_time_ms": max(assembly_times),
                    "p95_time_ms": sorted(assembly_times)[
                        int(0.95 * len(assembly_times))
                    ]
                    if assembly_times
                    else 0,
                },
            },
            "recommendations": self._generate_health_recommendations(
                avg_utilization,
                avg_assembly_time,
                redaction_rate,
                error_rate,
                layer_consistency,
            ),
        }

    def _generate_health_recommendations(
        self,
        avg_utilization: float,
        avg_assembly_time: float,
        redaction_rate: float,
        error_rate: float,
        layer_consistency: float,
    ) -> List[str]:
        """Generate recommendations based on context assembly health metrics"""

        recommendations = []

        if avg_utilization > 95:
            recommendations.append(
                "High token utilization - consider increasing token budget"
            )

        if avg_assembly_time > 1000:
            recommendations.append(
                "Slow context assembly - review layer processing efficiency"
            )

        if redaction_rate > 20:
            recommendations.append(
                "High redaction rate - review data filtering before assembly"
            )

        if error_rate > 5:
            recommendations.append("High error rate - review context assembly logic")

        if layer_consistency < 70:
            recommendations.append(
                "Inconsistent layer assembly - review layer ordering logic"
            )

        if not recommendations:
            recommendations.append(
                "Context assembly health looks good - continue monitoring"
            )

        return recommendations

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
        """Search snapshots with advanced filtering"""

        results = []

        for snapshot in self._snapshot_cache.values():
            # Apply filters
            if user_id and snapshot.user_id != user_id:
                continue
            if model and snapshot.model_target != model:
                continue
            if start_time and snapshot.timestamp < start_time:
                continue
            if end_time and snapshot.timestamp > end_time:
                continue
            if min_tokens and snapshot.total_tokens < min_tokens:
                continue
            if max_tokens and snapshot.total_tokens > max_tokens:
                continue

            # Apply text search on redacted content
            if query:
                snapshot_text = " ".join(
                    layer.get("content", "") for layer in snapshot.context_layers
                )
                if query.lower() not in snapshot_text.lower():
                    continue

            results.append(snapshot.to_dict())

        # Sort by timestamp
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results

    async def replay_context(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Replay context assembly for debugging purposes"""
        snapshot = await self.get_context_snapshot(request_id)
        if not snapshot:
            return None

        # Reconstruct the context for replay
        replay_data = {
            "request_id": request_id,
            "context_hash": snapshot["context_hash"],
            "reconstructed_context": "\n\n".join(
                f"[{layer.get('name', 'LAYER')}] {layer.get('content', '')}"
                for layer in snapshot["context_layers"]
            ),
            "token_usage": {
                "total": snapshot["total_tokens"],
                "remaining": snapshot["remaining_tokens"],
                "budget": snapshot["token_budget"],
            },
            "assembly_details": {
                "layers": len(snapshot["context_layers"]),
                "assembly_time": snapshot["assembly_time_ms"],
                "model_target": snapshot["model_target"],
            },
            "redaction_details": snapshot["redaction_details"],
        }

        return replay_data


# Global context snapshotter instance
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
    """Convenience function to capture context snapshots"""
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
