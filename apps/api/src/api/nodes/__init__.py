"""Self-hosted compute nodes: registry, heartbeat contract, and dispatch.

Local compute is a tier that sits above the cloud provider ladder, not a
member of it. See dispatch.py for why.
"""

from .client import (
    NodeRequestRejectedError,
    NodeSaturatedError,
    NodeStreamInterruptedError,
    NodeUnavailableError,
    invoke_node,
    stream_node,
)
from .config import NodeSettings, node_settings
from .dispatch import try_local_compute, try_local_compute_stream
from .models import NodeHeartbeat, NodeRecord, NodeStatus, NodeView
from .registry import NodeRegistry, Reservation, node_registry
from .router import router

__all__ = [
    "NodeHeartbeat",
    "NodeRecord",
    "NodeStatus",
    "NodeView",
    "NodeRegistry",
    "Reservation",
    "node_registry",
    "NodeSettings",
    "node_settings",
    "NodeUnavailableError",
    "NodeSaturatedError",
    "NodeRequestRejectedError",
    "NodeStreamInterruptedError",
    "invoke_node",
    "stream_node",
    "try_local_compute",
    "try_local_compute_stream",
    "router",
]
