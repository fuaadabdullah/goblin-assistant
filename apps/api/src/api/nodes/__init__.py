"""Self-hosted compute nodes: registry, heartbeat contract, and dispatch.

Local compute is a tier that sits above the cloud provider ladder, not a
member of it. See dispatch.py for why.
"""

from .client import NodeUnavailableError, invoke_node
from .config import NodeSettings, node_settings
from .dispatch import try_local_compute
from .models import NodeHeartbeat, NodeRecord, NodeStatus, NodeView
from .registry import NodeRegistry, node_registry
from .router import router

__all__ = [
    "NodeHeartbeat",
    "NodeRecord",
    "NodeStatus",
    "NodeView",
    "NodeRegistry",
    "node_registry",
    "NodeSettings",
    "node_settings",
    "NodeUnavailableError",
    "invoke_node",
    "try_local_compute",
    "router",
]
