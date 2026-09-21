"""Contracts for the Goblin node registry.

The inbound shape is fixed by what `goblin-node-agent` already publishes; see
that repo's README ("Heartbeat"). Changing these field names breaks deployed
nodes, so treat them as a wire contract rather than an internal model.
"""

from __future__ import annotations

import time
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

NodeStatus = Literal["online", "degraded", "offline"]


class NodeHeartbeat(BaseModel):
    """What a node POSTs to /api/v1/nodes/heartbeat."""

    node_id: str = Field(..., min_length=1, max_length=128)
    node_type: str = Field(default="inference", max_length=64)
    status: NodeStatus = "online"
    backend: str = Field(default="unknown", max_length=64)
    gpu: str = Field(default="", max_length=256)
    models: List[str] = Field(default_factory=list)
    active_jobs: int = Field(default=0, ge=0)
    max_concurrency: int = Field(default=1, ge=0)
    # The address the router should dial. A node behind a tunnel cannot infer
    # its own reachable address, so this is the node's to declare.
    endpoint: Optional[str] = None


class NodeRecord(BaseModel):
    """A node as the registry holds it.

    `last_heartbeat` is a monotonic timestamp, not wall clock: staleness is a
    duration measurement, and a clock adjustment must not make a live node look
    stale (or a dead one look fresh).
    """

    node_id: str
    node_type: str
    status: NodeStatus
    backend: str
    gpu: str
    models: List[str]
    active_jobs: int
    max_concurrency: int
    endpoint: Optional[str]
    last_heartbeat: float
    first_seen: float
    heartbeat_count: int = 0
    # Set when a dispatch to this node fails, so one bad node does not get
    # retried on every request until its heartbeat happens to lapse.
    consecutive_failures: int = 0

    @classmethod
    def from_heartbeat(
        cls,
        hb: NodeHeartbeat,
        *,
        now: float,
        previous: Optional["NodeRecord"] = None,
    ) -> "NodeRecord":
        return cls(
            node_id=hb.node_id,
            node_type=hb.node_type,
            status=hb.status,
            backend=hb.backend,
            gpu=hb.gpu,
            models=list(hb.models),
            active_jobs=hb.active_jobs,
            max_concurrency=hb.max_concurrency,
            endpoint=hb.endpoint or (previous.endpoint if previous else None),
            last_heartbeat=now,
            first_seen=previous.first_seen if previous else now,
            heartbeat_count=(previous.heartbeat_count + 1) if previous else 1,
            # A fresh heartbeat is evidence the node recovered.
            consecutive_failures=0,
        )

    def age_seconds(self, now: Optional[float] = None) -> float:
        return (now if now is not None else time.monotonic()) - self.last_heartbeat

    def is_fresh(self, ttl_seconds: float, now: Optional[float] = None) -> bool:
        return self.age_seconds(now) <= ttl_seconds

    def has_capacity(self) -> bool:
        return self.active_jobs < self.max_concurrency

    def serves_model(self, model: str) -> bool:
        return model in self.models


class NodeView(BaseModel):
    """Read model for the /nodes endpoints.

    Exposes `age_seconds` and the *effective* status rather than the raw
    stored one, so an operator sees what the router sees.
    """

    node_id: str
    node_type: str
    status: NodeStatus
    backend: str
    gpu: str
    models: List[str]
    active_jobs: int
    max_concurrency: int
    endpoint: Optional[str]
    age_seconds: float
    heartbeat_count: int
    consecutive_failures: int
    eligible: bool
