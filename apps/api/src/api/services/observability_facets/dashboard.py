from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List

import structlog

from ...observability.context_snapshotter import context_snapshotter
from ...observability.decision_logger import decision_logger
from ...observability.memory_logger import memory_promotion_logger
from ...observability.metrics_collector import metrics_collector
from ...observability.retrieval_tracer import retrieval_tracer

logger = structlog.get_logger()


class ObservabilityDashboardFacet:
    def __init__(self, owner: Any):
        self._owner = owner

    def _ensure_metric_defaults(self) -> None:
        if not hasattr(self._owner, "memory_health"):
            self._owner.memory_health = {
                "promotion_rejection_rate": 0.0,
                "contradiction_rate": 0.0,
                "decay_events": 0,
            }
        if not hasattr(self._owner, "retrieval_quality"):
            self._owner.retrieval_quality = {
                "avg_chunks_per_request": 0,
                "token_utilization_percent": 0,
                "retrieval_hit_rate": 0,
            }
        if not hasattr(self._owner, "cost_control"):
            self._owner.cost_control = {
                "embeddings_per_conversation": 0,
                "tokens_spent_per_tier": {},
                "cache_hit_rate": 0,
            }

    def get_memory_debug_info(self, user_id: str) -> Dict[str, Any]:
        try:
            if self._owner.memory_promotions:
                events = [
                    {
                        "candidate_text": e.candidate_text,
                        "source_type": e.source,
                        "confidence_score": e.confidence_score,
                        "timestamp": e.timestamp,
                        "source_conversation": e.conversation_id,
                    }
                    for e in self._owner.memory_promotions
                    if e.user_id == user_id
                ]
            else:
                events = []

            import asyncio  # noqa: PLC0415

            if not events:
                try:
                    loop = asyncio.get_running_loop()
                    future = asyncio.run_coroutine_threadsafe(
                        memory_promotion_logger.get_promotion_history(user_id=user_id, limit=20),
                        loop,
                    )
                    events = future.result(timeout=2)
                except (RuntimeError, TimeoutError, Exception):
                    events = []

            return {
                "user_id": user_id,
                "memory_items": [
                    {
                        "content": e.get("candidate_text", ""),
                        "source": e.get("source_type", ""),
                        "confidence": e.get("confidence_score", 0.0),
                        "timestamp": e.get("timestamp", ""),
                        "source_reference": e.get("source_conversation", ""),
                    }
                    for e in events[-20:]
                ],
                "memory_health": {
                    "total_items": len(events),
                    "avg_confidence": (
                        sum(e.get("confidence_score", 0.0) for e in events) / max(len(events), 1)
                    ),
                    "promotion_rejection_rate": 0.0,
                    "contradiction_rate": 0.0,
                },
                "last_updated": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error("Failed to get memory debug info", user_id=user_id, error=str(e))
            return {"error": str(e)}

    def get_retrieval_trace(self, request_id: str) -> Dict[str, Any]:
        try:
            if self._owner.retrieval_traces:
                trace = next(
                    (
                        t
                        for t in reversed(self._owner.retrieval_traces)
                        if t.request_id == request_id
                    ),
                    None,
                )
                if trace:
                    return {
                        "request_id": trace.request_id,
                        "user_id": trace.user_id,
                        "model_selected": trace.model_selected,
                        "token_budget": trace.token_budget,
                        "retrieval_items": trace.items_retrieved,
                        "scoring_breakdown": trace.scoring_breakdown,
                        "token_allocation": trace.token_allocation,
                        "timestamp": trace.timestamp,
                        "analysis": {
                            "items_cut_due_to_budget": sum(
                                1 for item in trace.items_retrieved if item.get("truncated")
                            ),
                            "avg_relevance_score": (
                                sum(
                                    item.get("relevance_score", 0.0)
                                    for item in trace.items_retrieved
                                )
                                / max(len(trace.items_retrieved), 1)
                            ),
                            "tier_efficiency": {},
                        },
                    }

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    retrieval_tracer.get_retrieval_trace(request_id), loop
                )
                trace = future.result(timeout=2)
            except (RuntimeError, TimeoutError, Exception):
                trace = None

            if not trace:
                return {"error": f"No trace found for request_id: {request_id}"}

            return {
                "request_id": trace.get("request_id", request_id),
                "user_id": trace.get("user_id"),
                "model_selected": trace.get("model_selected", ""),
                "token_budget": trace.get("token_budget", 0),
                "retrieval_items": trace.get("items_retrieved", []),
                "scoring_breakdown": trace.get("tier_breakdown", {}),
                "token_allocation": {
                    tier: stats.get("total_tokens", 0)
                    for tier, stats in trace.get("tier_breakdown", {}).items()
                },
                "timestamp": trace.get("timestamp", ""),
                "analysis": {
                    "items_cut_due_to_budget": sum(
                        1 for item in trace.get("items_retrieved", []) if item.get("truncated")
                    ),
                    "avg_relevance_score": (
                        sum(
                            item.get("relevance_score", 0.0)
                            for item in trace.get("items_retrieved", [])
                        )
                        / max(len(trace.get("items_retrieved", [])), 1)
                    ),
                    "tier_efficiency": {},
                },
            }
        except Exception as e:
            logger.error("Failed to get retrieval trace", request_id=request_id, error=str(e))
            return {"error": str(e)}

    def get_write_decisions(self, conversation_id: str) -> Dict[str, Any]:
        try:
            if self._owner.write_decisions:
                decisions = [
                    d
                    for d in self._owner.write_decisions
                    if d.get("conversation_id") == conversation_id
                ]
            else:
                decisions = []

            import asyncio  # noqa: PLC0415

            if not decisions:
                try:
                    loop = asyncio.get_running_loop()
                    future = asyncio.run_coroutine_threadsafe(
                        decision_logger.get_decision_history(
                            conversation_id=conversation_id, limit=100
                        ),
                        loop,
                    )
                    decisions = future.result(timeout=2)
                except (RuntimeError, TimeoutError, Exception):
                    decisions = []

            return {
                "conversation_id": conversation_id,
                "decisions": [
                    {
                        "message_id": d.get("message_id", ""),
                        "message_role": d.get("classification", {}).get("type", "unknown"),
                        "classified_type": d.get("classification", {}).get("type", "unknown"),
                        "embedded": d.get("decisions", {}).get("embedded", False),
                        "summarized": d.get("decisions", {}).get("summarized", False),
                        "discarded": d.get("decisions", {}).get("discarded", False),
                        "reason_codes": d.get("classification", {}).get("reason_codes", []),
                        "confidence": d.get("classification", {}).get("confidence", 0.0),
                        "timestamp": d.get("timestamp", ""),
                    }
                    for d in decisions
                ],
                "summary": {
                    "total_decisions": len(decisions),
                    "embedding_rate": sum(
                        1 for d in decisions if d.get("decisions", {}).get("embedded", False)
                    )
                    / max(len(decisions), 1),
                    "summarization_rate": sum(
                        1 for d in decisions if d.get("decisions", {}).get("summarized", False)
                    )
                    / max(len(decisions), 1),
                    "discard_rate": sum(
                        1 for d in decisions if d.get("decisions", {}).get("discarded", False)
                    )
                    / max(len(decisions), 1),
                    "avg_confidence": sum(
                        d.get("classification", {}).get("confidence", 0.0) for d in decisions
                    )
                    / max(len(decisions), 1),
                },
            }
        except Exception as e:
            logger.error(
                "Failed to get write decisions",
                conversation_id=conversation_id,
                error=str(e),
            )
            return {"error": str(e)}

    def get_context_snapshot(self, request_id: str) -> Dict[str, Any]:
        try:
            if self._owner.context_snapshots:
                snapshot = next(
                    (
                        s
                        for s in reversed(self._owner.context_snapshots)
                        if s.request_id == request_id
                    ),
                    None,
                )
                if snapshot:
                    return {
                        "request_id": snapshot.request_id,
                        "user_id": snapshot.user_id,
                        "context_hash": snapshot.context_hash,
                        "redacted_snapshot": snapshot.redacted_snapshot,
                        "total_token_usage": snapshot.total_token_usage,
                        "assembly_details": snapshot.assembly_details,
                        "timestamp": snapshot.timestamp,
                    }

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    context_snapshotter.get_context_snapshot(request_id), loop
                )
                snapshot = future.result(timeout=2)
            except (RuntimeError, TimeoutError, Exception):
                snapshot = None

            if not snapshot:
                return {"error": f"No snapshot found for request_id: {request_id}"}

            return {
                "request_id": snapshot.get("request_id", request_id),
                "user_id": snapshot.get("user_id"),
                "context_hash": snapshot.get("context_hash", ""),
                "redacted_snapshot": {
                    "layers": snapshot.get("context_layers", []),
                    "total_tokens": snapshot.get("total_tokens", 0),
                    "remaining_tokens": snapshot.get("remaining_tokens", 0),
                },
                "total_token_usage": snapshot.get("total_tokens", 0),
                "assembly_details": {},
                "timestamp": snapshot.get("timestamp", ""),
            }
        except Exception as e:
            logger.error("Failed to get context snapshot", request_id=request_id, error=str(e))
            return {"error": str(e)}

    def get_critical_metrics(self) -> Dict[str, Any]:
        try:
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    metrics_collector.collect_system_metrics(user_id=None, time_window_hours=24),
                    loop,
                )
                metrics = future.result(timeout=2)
                metrics_data = {
                    "memory_health": {
                        "avg_memories_per_user": 0,
                        "promotion_rejection_rate": (
                            100 - (metrics.memory_health.get("score", 0) or 0)
                        )
                        / 100
                        if metrics.memory_health.get("status") != "no_data"
                        else 0,
                        "contradiction_rate": 0,
                        "decay_events": 0,
                    },
                    "retrieval_quality": {
                        "avg_chunks_per_request": metrics.retrieval_quality.get(
                            "total_retrievals", 0
                        ),
                        "token_utilization_percent": metrics.retrieval_quality.get(
                            "token_utilization", 0
                        ),
                        "retrieval_hit_rate": metrics.retrieval_quality.get("avg_relevance", 0),
                    },
                    "cost_control": {
                        "embeddings_per_conversation": 0,
                        "tokens_spent_per_tier": {},
                        "cache_hit_rate": 0,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except (RuntimeError, TimeoutError, Exception):
                metrics_data = {
                    "memory_health": {
                        "avg_memories_per_user": 0,
                        "promotion_rejection_rate": 0,
                        "contradiction_rate": 0,
                        "decay_events": 0,
                    },
                    "retrieval_quality": {
                        "avg_chunks_per_request": 0,
                        "token_utilization_percent": 0,
                        "retrieval_hit_rate": 0,
                    },
                    "cost_control": {
                        "embeddings_per_conversation": 0,
                        "tokens_spent_per_tier": {},
                        "cache_hit_rate": 0,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

            metrics_data["memory_health"].update(getattr(self._owner, "memory_health", {}))
            metrics_data["retrieval_quality"].update(getattr(self._owner, "retrieval_quality", {}))
            metrics_data["cost_control"].update(getattr(self._owner, "cost_control", {}))
            self._owner.memory_health = metrics_data["memory_health"]
            self._owner.retrieval_quality = metrics_data["retrieval_quality"]
            self._owner.cost_control = metrics_data["cost_control"]
            return metrics_data
        except Exception as e:
            logger.error("Failed to get critical metrics", error=str(e))
            return {
                "memory_health": {},
                "retrieval_quality": {},
                "cost_control": {},
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    def check_alerts(self) -> List[Dict[str, Any]]:
        try:
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    metrics_collector.collect_system_metrics(user_id=None, time_window_hours=24),
                    loop,
                )
                metrics = future.result(timeout=2)
            except (RuntimeError, TimeoutError, Exception):
                metrics = None

            alerts: List[Dict[str, Any]] = []

            memory_health = dict(getattr(self._owner, "memory_health", {}) or {})
            retrieval_quality = dict(getattr(self._owner, "retrieval_quality", {}) or {})

            if metrics:
                if not memory_health:
                    memory_health = dict(metrics.memory_health)
                if not retrieval_quality:
                    retrieval_quality = dict(metrics.retrieval_quality)

                if metrics.memory_health.get("status") == "critical":
                    alerts.append(
                        {
                            "type": "memory_promotion_spike",
                            "severity": "warning",
                            "message": f"Memory health is critical: score={metrics.memory_health.get('score', 0)}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                if metrics.retrieval_quality.get("status") == "critical":
                    alerts.append(
                        {
                            "type": "retrieval_empty",
                            "severity": "critical",
                            "message": f"Retrieval quality is critical: score={metrics.retrieval_quality.get('score', 0)}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                token_util = metrics.retrieval_quality.get("token_utilization", 0)
                if token_util > 95:
                    alerts.append(
                        {
                            "type": "token_budget_exceeded",
                            "severity": "warning",
                            "message": f"Token budget frequently exceeded: {token_util:.1f}%",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                if metrics.context_assembly.get("status") == "critical":
                    alerts.append(
                        {
                            "type": "memory_contradiction",
                            "severity": "critical",
                            "message": f"Context assembly is critical: score={metrics.context_assembly.get('score', 0)}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            if memory_health.get("promotion_rejection_rate", 0) > 0.8:
                alerts.append(
                    {
                        "type": "memory_promotion_spike",
                        "severity": "warning",
                        "message": (
                            f"Memory promotion rejection rate is high: "
                            f"{memory_health.get('promotion_rejection_rate', 0):.2f}"
                        ),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

            if retrieval_quality.get("retrieval_hit_rate", 1) < 0.1:
                alerts.append(
                    {
                        "type": "retrieval_empty",
                        "severity": "critical",
                        "message": (
                            f"Retrieval quality is critical: "
                            f"score={retrieval_quality.get('retrieval_hit_rate', 0)}"
                        ),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

            return alerts
        except Exception as e:
            logger.error("Failed to check alerts", error=str(e))
            return [
                {
                    "type": "system_error",
                    "severity": "warning",
                    "message": f"Alert check failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]

    def export_observability_data(self) -> Dict[str, Any]:
        try:
            import asyncio  # noqa: PLC0415

            decisions: List[Dict[str, Any]] = []
            promotions: List[Dict[str, Any]] = []
            retrievals: List[Dict[str, Any]] = []
            snapshots: List[Dict[str, Any]] = []

            try:
                loop = asyncio.get_running_loop()

                futures = {
                    "decisions": asyncio.run_coroutine_threadsafe(
                        decision_logger.get_decision_history(conversation_id="", limit=100),
                        loop,
                    ),
                    "promotions": asyncio.run_coroutine_threadsafe(
                        memory_promotion_logger.get_promotion_history(limit=50),
                        loop,
                    ),
                    "retrievals": asyncio.run_coroutine_threadsafe(
                        retrieval_tracer.get_retrieval_history(limit=20),
                        loop,
                    ),
                }

                for key, future in futures.items():
                    try:
                        result = future.result(timeout=2)
                        if key == "decisions":
                            decisions = result
                        elif key == "promotions":
                            promotions = result
                        elif key == "retrievals":
                            retrievals = result
                    except (TimeoutError, Exception):
                        pass

            except (RuntimeError, Exception):
                pass

            if not decisions and self._owner.write_decisions:
                decisions = list(self._owner.write_decisions)
            if not promotions and self._owner.memory_promotions:
                promotions = [asdict(item) for item in self._owner.memory_promotions]
            if not retrievals and self._owner.retrieval_traces:
                retrievals = [asdict(item) for item in self._owner.retrieval_traces]
            if not snapshots and self._owner.context_snapshots:
                snapshots = [asdict(item) for item in self._owner.context_snapshots]

            return {
                "write_decisions": decisions,
                "memory_promotions": promotions,
                "retrieval_traces": retrievals,
                "context_snapshots": snapshots,
                "metrics": self.get_critical_metrics(),
                "alerts": self.check_alerts(),
                "export_timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error("Failed to export observability data", error=str(e))
            return {
                "write_decisions": [],
                "memory_promotions": [],
                "retrieval_traces": [],
                "context_snapshots": [],
                "metrics": {},
                "alerts": [],
                "export_timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }
