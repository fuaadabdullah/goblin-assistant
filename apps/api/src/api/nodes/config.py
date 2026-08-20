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
    # Master switch, default OFF. Local compute is a deployment gate, not a
    # default: an environment opts in only once the tunnel, the mTLS material,
    # the heartbeat secret and a reachable node are all actually in place.
    enabled: bool = field(default_factory=lambda: _flag("GOBLIN_LOCAL_NODES_ENABLED", "false"))

    # Shared secret a node presents to register. There is no default and no
    # fallback: with this unset the heartbeat endpoint refuses every request,
    # because an unauthenticated node control plane lets anyone redirect real
    # user prompts to a host of their choosing.
    registration_secret: str = field(
        default_factory=lambda: _env("GOBLIN_NODE_REGISTRATION_SECRET", "")
    )

    # Secret for the management routes (list / inspect / evict). Deliberately
    # SEPARATE from registration_secret, because the two have very different
    # blast radii: the registration secret is copied onto every node in the
    # fleet, so reusing it here would let any node -- or anyone who
    # compromised one -- enumerate and evict the rest.
    #
    # This exists because Goblin has no role model: UserModel has no admin or
    # superuser column, so `get_current_user` proves somebody is logged in,
    # not that they are an operator. Requiring a secret is honest about that.
    # Replace it with a real authorization dependency once roles exist.
    operator_secret: str = field(default_factory=lambda: _env("GOBLIN_NODE_OPERATOR_SECRET", ""))

    # Hosts a node is permitted to advertise as its endpoint, comma separated.
    # Empty means "no allowlist", which is acceptable only because the
    # heartbeat is authenticated -- set it in production anyway, so a leaked
    # secret cannot be escalated into prompt exfiltration.
    endpoint_allowlist: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            h.strip().lower()
            for h in _env("GOBLIN_NODE_ENDPOINT_ALLOWLIST", "").split(",")
            if h.strip()
        )
    )

    # Permit http:// and non-loopback plaintext endpoints. Development only.
    allow_insecure_endpoints: bool = field(
        default_factory=lambda: _flag("GOBLIN_NODE_ALLOW_INSECURE_ENDPOINTS", "false")
    )

    # A heartbeat older than this means offline. 90s tolerates two dropped
    # beats against the agent's 30s default before eviction.
    heartbeat_ttl_seconds: float = field(
        default_factory=lambda: float(_env("GOBLIN_NODE_HEARTBEAT_TTL", "90"))
    )

    # Timeouts are split because the two failures are nothing alike.
    #
    # A killed process refuses the connection instantly, but a blackholed
    # tunnel or a firewall that drops packets silently does not -- the SYN
    # just goes nowhere. Under a single 60s budget that turns "the computer
    # is not there" into a minute of dead air before the cloud is tried,
    # which is exactly the "local-first made Goblin slow" failure this tier
    # must never cause.
    #
    # So: discovering a node is unreachable is capped tight, while a 3060
    # legitimately taking its time over a long answer is left alone.
    connect_timeout_seconds: float = field(
        default_factory=lambda: float(_env("GOBLIN_NODE_CONNECT_TIMEOUT", "3"))
    )
    read_timeout_seconds: float = field(
        default_factory=lambda: float(_env("GOBLIN_NODE_TIMEOUT", "300"))
    )
    write_timeout_seconds: float = field(
        default_factory=lambda: float(_env("GOBLIN_NODE_WRITE_TIMEOUT", "10"))
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
