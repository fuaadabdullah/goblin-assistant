"""Settings for the local-compute tier."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _flag(key: str, default: str = "true") -> bool:
    return _env(key, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class NodeSettings:
    # Master switch. Off means the router behaves exactly as it did before
    # local compute existed -- the safest possible rollback.
    enabled: bool = field(default_factory=lambda: _flag("GOBLIN_LOCAL_NODES_ENABLED", "true"))

    # A heartbeat older than this means offline. 90s tolerates two dropped
    # beats against the agent's 30s default before eviction.
    heartbeat_ttl_seconds: float = field(
        default_factory=lambda: float(_env("GOBLIN_NODE_HEARTBEAT_TTL", "90"))
    )

    # How long to wait on a node before giving up and using the cloud. Kept
    # short: the whole value of the fallback is that the user does not sit
    # through a dead node's timeout.
    dispatch_timeout_seconds: float = field(
        default_factory=lambda: float(_env("GOBLIN_NODE_TIMEOUT", "60"))
    )

    # Consecutive dispatch failures before a node is shed without waiting for
    # its heartbeat to lapse.
    max_consecutive_failures: int = field(
        default_factory=lambda: int(_env("GOBLIN_NODE_MAX_FAILURES", "3"))
    )

    # mTLS material the API presents when calling a node agent. Without a
    # client cert the node will drop us at the handshake, by design.
    client_certfile: str = field(default_factory=lambda: _env("GOBLIN_NODE_CLIENT_CERT", ""))
    client_keyfile: str = field(default_factory=lambda: _env("GOBLIN_NODE_CLIENT_KEY", ""))
    ca_certfile: str = field(default_factory=lambda: _env("GOBLIN_NODE_CA_CERT", ""))

    # Model asked of a node when the caller did not name one.
    default_model: str = field(
        default_factory=lambda: _env("GOBLIN_NODE_DEFAULT_MODEL", "llama3.1:8b")
    )


node_settings = NodeSettings()
