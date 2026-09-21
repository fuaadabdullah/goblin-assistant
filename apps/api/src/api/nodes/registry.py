"""In-process registry of self-hosted compute nodes.

Deliberately in-memory. Nodes re-announce themselves every ~30s, so a restart
costs at most one heartbeat interval of blindness -- cheaper than the
consistency problems of persisting state that is stale the moment it is
written.

The tradeoff worth knowing: with multiple API workers, each worker keeps its
own view. A node heartbeats to whichever worker load balancing picks, so a
given worker may not know about a node it has not personally heard from. That
is acceptable while local compute is an optimisation with a cloud fallback --
the worst case is a request going to the cloud that could have gone local. It
would NOT be acceptable if local nodes ever became the only path; that is when
this moves to Redis or the database.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

import structlog

from .config import node_settings
from .models import NodeHeartbeat, NodeRecord, NodeStatus, NodeView

logger = structlog.get_logger()


class NodeRegistry:
    """Thread-safe store of known nodes, keyed by node_id."""

    def __init__(self, *, ttl_seconds: Optional[float] = None) -> None:
        self._nodes: Dict[str, NodeRecord] = {}
        self._lock = threading.RLock()
        self._ttl_override = ttl_seconds

    @property
    def ttl_seconds(self) -> float:
        if self._ttl_override is not None:
            return self._ttl_override
        return node_settings.heartbeat_ttl_seconds

    # -- writes -------------------------------------------------------------

    def upsert(self, hb: NodeHeartbeat, *, now: Optional[float] = None) -> NodeRecord:
        """Record a heartbeat, creating the node if it is new."""
        stamp = now if now is not None else time.monotonic()
        with self._lock:
            previous = self._nodes.get(hb.node_id)
            record = NodeRecord.from_heartbeat(hb, now=stamp, previous=previous)
            self._nodes[hb.node_id] = record

        if previous is None:
            logger.info(
                "node_registered",
                node_id=record.node_id,
                gpu=record.gpu,
                models=record.models,
                endpoint=record.endpoint,
            )
        elif previous.status != record.status:
            logger.info(
                "node_status_changed",
                node_id=record.node_id,
                previous=previous.status,
                current=record.status,
            )
        return record

    def record_failure(self, node_id: str) -> None:
        """Note that a dispatch to this node failed.

        Failing nodes are shed immediately rather than left eligible until
        their heartbeat lapses -- otherwise every request in the next 90s
        pays the timeout before falling through to the cloud.
        """
        with self._lock:
            record = self._nodes.get(node_id)
            if record is None:
                return
            record.consecutive_failures += 1
            failures = record.consecutive_failures
        logger.warning("node_dispatch_failed", node_id=node_id, consecutive_failures=failures)

    def record_success(self, node_id: str) -> None:
        with self._lock:
            record = self._nodes.get(node_id)
            if record is not None:
                record.consecutive_failures = 0

    def forget(self, node_id: str) -> bool:
        with self._lock:
            return self._nodes.pop(node_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()

    # -- reads --------------------------------------------------------------

    def get(self, node_id: str) -> Optional[NodeRecord]:
        with self._lock:
            return self._nodes.get(node_id)

    def all(self) -> List[NodeRecord]:
        with self._lock:
            return list(self._nodes.values())

    def effective_status(self, record: NodeRecord, *, now: Optional[float] = None) -> NodeStatus:
        """Status accounting for staleness.

        A node that stopped heartbeating is offline no matter what its last
        message claimed -- silence is the only signal we get when a node is
        yanked from the wall.
        """
        if not record.is_fresh(self.ttl_seconds, now):
            return "offline"
        return record.status

    def is_eligible(
        self,
        record: NodeRecord,
        *,
        model: Optional[str] = None,
        now: Optional[float] = None,
    ) -> bool:
        """Every condition that must hold before we send this node work."""
        if self.effective_status(record, now=now) != "online":
            return False
        if not record.has_capacity():
            return False
        if record.consecutive_failures >= node_settings.max_consecutive_failures:
            return False
        if model is not None and not record.serves_model(model):
            return False
        return True

    def eligible_nodes(
        self,
        *,
        model: Optional[str] = None,
        now: Optional[float] = None,
    ) -> List[NodeRecord]:
        """Nodes that may take work right now, most idle first.

        Ordering is deliberately trivial: with one node it does not matter, and
        real multi-node scheduling (VRAM fit, model residency, locality) is a
        separate problem that should not be half-solved here.
        """
        stamp = now if now is not None else time.monotonic()
        with self._lock:
            candidates = [
                r for r in self._nodes.values() if self.is_eligible(r, model=model, now=stamp)
            ]
        return sorted(candidates, key=lambda r: (r.active_jobs, r.node_id))

    def view(self, record: NodeRecord, *, now: Optional[float] = None) -> NodeView:
        stamp = now if now is not None else time.monotonic()
        return NodeView(
            node_id=record.node_id,
            node_type=record.node_type,
            status=self.effective_status(record, now=stamp),
            backend=record.backend,
            gpu=record.gpu,
            models=record.models,
            active_jobs=record.active_jobs,
            max_concurrency=record.max_concurrency,
            endpoint=record.endpoint,
            age_seconds=round(record.age_seconds(stamp), 2),
            heartbeat_count=record.heartbeat_count,
            consecutive_failures=record.consecutive_failures,
            eligible=self.is_eligible(record, now=stamp),
        )


# Process-wide singleton, mirroring api.routing.router_registry.registry.
node_registry = NodeRegistry()
