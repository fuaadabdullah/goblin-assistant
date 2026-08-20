"""Validation for the endpoint a node advertises.

This exists because `endpoint` is the single most dangerous field in the
heartbeat contract. Dispatch sends the *actual user prompt* to whatever
address it contains, using the API's node TLS identity. An unvalidated string
here is a prompt-exfiltration and SSRF primitive, not a cosmetic issue.

Authentication on the heartbeat is the primary control; this is the second
layer, so that a leaked registration secret cannot be escalated into
"redirect Goblin's traffic anywhere I like".
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from .config import node_settings

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


class InvalidEndpointError(ValueError):
    """The advertised endpoint is not one we are willing to dial."""


def _is_loopback(host: str) -> bool:
    if host.lower() in _LOOPBACK_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_endpoint(endpoint: str, *, settings=None) -> str:
    """Return the endpoint if we are willing to send prompts to it.

    Raises InvalidEndpointError otherwise. Deliberately strict: a node that cannot
    describe itself acceptably simply does not get traffic.
    """
    cfg = settings or node_settings

    if not endpoint or not endpoint.strip():
        raise InvalidEndpointError("endpoint is empty")

    parts = urlsplit(endpoint.strip())

    if parts.scheme not in {"http", "https"}:
        raise InvalidEndpointError("scheme must be http or https, got {!r}".format(parts.scheme))

    # Credentials in the URL would be sent onward by httpx; there is no
    # legitimate reason for a node to embed them.
    if parts.username or parts.password:
        raise InvalidEndpointError("endpoint must not contain credentials")

    if parts.query or parts.fragment:
        raise InvalidEndpointError("endpoint must not contain a query or fragment")

    host = parts.hostname
    if not host:
        raise InvalidEndpointError("endpoint has no host")

    # Plaintext is only ever acceptable to loopback, where there is no network
    # to eavesdrop on. Anything else must be TLS, because the node's whole
    # security model is mutual TLS.
    if parts.scheme == "http" and not (_is_loopback(host) or cfg.allow_insecure_endpoints):
        raise InvalidEndpointError(
            "http endpoints are only permitted to loopback "
            "(set GOBLIN_NODE_ALLOW_INSECURE_ENDPOINTS=true for local development)"
        )

    if cfg.endpoint_allowlist and host.lower() not in cfg.endpoint_allowlist:
        raise InvalidEndpointError(
            "host {!r} is not in GOBLIN_NODE_ENDPOINT_ALLOWLIST".format(host)
        )

    return endpoint.strip().rstrip("/")
