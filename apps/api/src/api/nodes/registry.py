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

import itertools
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import structlog

from .config import node_settings
from .models import NodeHeartbeat, NodeRecord, NodeStatus, NodeView

logger = structlog.get_logger()

_reservation_ids = itertools.count(1)


@dataclass(frozen=True)
class Reservation:
    """One API-side claim on a node slot, released exactly once."""

    node_id: str
    reservation_id: int
    reserved_at: float


class NodeRegistry:
    """Thread-safe store of known nodes, keyed by node_id."""

    def __init__(self, *, ttl_seconds: Optional[float] = None) -> None:
        self._nodes: Dict[str, NodeRecord] = {}
        # In-process reservations close the race between heartbeats: two API
        # requests must not both claim the final slot before active_jobs updates.
        # Keyed node_id -> reservation_id -> Reservation.
        self._inflight: Dict[str, Dict[int, Reservation]] = {}
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

    def record_failure(self, node_id: str, *, now: Optional[float] = None) -> None:
        """Note that a dispatch to this node failed.

        Failing nodes are shed immediately rather than left eligible until
        their heartbeat lapses -- otherwise every request in the next 90s
        pays the timeout before falling through to the cloud.
        """
        stamp = now if now is not None else time.monotonic()
        with self._lock:
            record = self._nodes.get(node_id)
            if record is None:
                return
            record.consecutive_failures += 1
            record.last_failure_at = stamp
            failures = record.consecutive_failures
        logger.warning("node_dispatch_failed", node_id=node_id, consecutive_failures=failures)

    def record_success(self, node_id: str) -> None:
        with self._lock:
            record = self._nodes.get(node_id)
            if record is not None:
                record.consecutive_failures = 0
                record.last_failure_at = None

    def forget(self, node_id: str) -> bool:
        with self._lock:
            self._inflight.pop(node_id, None)
            return self._nodes.pop(node_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._inflight.clear()

    def try_reserve(
        self,
        node_id: str,
        *,
        model: Optional[str] = None,
        now: Optional[float] = None,
    ) -> Optional[Reservation]:
        """Atomically reserve one local dispatch slot if the node is eligible.

        Returns the reservation (truthy) or None. Pass it back to release().
        """
        stamp = now if now is not None else time.monotonic()
        with self._lock:
            record = self._nodes.get(node_id)
            if record is None or not self._is_eligible_locked(record, model=model, now=stamp):
                return None
            reservation = Reservation(
                node_id=node_id,
                reservation_id=next(_reservation_ids),
                reserved_at=stamp,
            )
            self._inflight.setdefault(node_id, {})[reservation.reservation_id] = reservation
            return reservation

    def release(self, node_id: str, reservation: Optional[Reservation] = None) -> None:
        """Release an API-side dispatch reservation.

        Without an explicit reservation the oldest one is released, which is
        the right choice for callers that only ever hold one.
        """
        with self._lock:
            held = self._inflight.get(node_id)
            if not held:
                return
            if reservation is not None:
                held.pop(reservation.reservation_id, None)
            else:
                held.pop(min(held), None)
            if not held:
                self._inflight.pop(node_id, None)

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

    def _effective_active_jobs_locked(self, record: NodeRecord) -> int:
        """Load the node is carrying, as best this worker can tell.

        The last heartbeat's active_jobs already includes any of our
        reservations that were in flight when it was sent, but none made
        since. So: reported load plus reservations newer than that heartbeat,
        and never less than what this worker alone has in flight (the node
        may have finished other callers' jobs since it reported).
        """
        held = self._inflight.get(record.node_id, {})
        since_heartbeat = sum(1 for r in held.values() if r.reserved_at >= record.last_heartbeat)
        return max(record.active_jobs + since_heartbeat, len(held))

    def _is_shed_locked(self, record: NodeRecord, now: float) -> bool:
        """Whether the failure breaker is open for this node.

        A heartbeat does not close it: it proves the control plane is alive,
        not that inference works. Instead the breaker goes half-open after a
        cooldown, and the next dispatch is the probe -- success closes it,
        failure re-arms the cooldown.
        """
        if record.consecutive_failures < node_settings.max_consecutive_failures:
            return False
        if record.last_failure_at is None:
            return False
        return (now - record.last_failure_at) < node_settings.failure_cooldown_seconds

    def _is_eligible_locked(
        self,
        record: NodeRecord,
        *,
        model: Optional[str] = None,
        now: Optional[float] = None,
    ) -> bool:
        stamp = now if now is not None else time.monotonic()
        if self.effective_status(record, now=stamp) != "online":
            return False
        if self._effective_active_jobs_locked(record) >= record.max_concurrency:
            return False
        if self._is_shed_locked(record, stamp):
            return False
        if model is not None and not record.serves_model(model):
            return False
        return True

    def is_eligible(
        self,
        record: NodeRecord,
        *,
        model: Optional[str] = None,
        now: Optional[float] = None,
    ) -> bool:
        """Every condition that must hold before we send this node work."""
        with self._lock:
            return self._is_eligible_locked(record, model=model, now=now)

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
                r
                for r in self._nodes.values()
                if self._is_eligible_locked(r, model=model, now=stamp)
            ]
            loads = {r.node_id: self._effective_active_jobs_locked(r) for r in candidates}
        return sorted(candidates, key=lambda r: (loads[r.node_id], r.node_id))

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
