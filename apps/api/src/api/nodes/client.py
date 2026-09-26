"""mTLS client for talking to a goblin-node-agent.

Every failure mode here is non-fatal by contract: the caller's job is to fall
through to the cloud, so this module raises a single narrow exception type and
never lets an httpx/ssl detail escape into routing code.
"""

from __future__ import annotations

import ssl
from typing import Any, Dict, Optional

import httpx
import structlog

from .config import node_settings

logger = structlog.get_logger()


class NodeUnavailableError(RuntimeError):
    """The node could not serve this request. Always recoverable via cloud."""


_ssl_context: Optional[ssl.SSLContext] = None
_ssl_context_built = False


def build_ssl_context() -> ssl.SSLContext | bool:
    """Build (once) the client context carrying our node-fleet identity.

    Returns True -- httpx's "verify using system CAs" -- when no custom trust
    is configured, so a node fronted by a publicly-trusted certificate still
    works without extra setup.
    """
    global _ssl_context, _ssl_context_built
    if _ssl_context_built:
        return _ssl_context if _ssl_context is not None else True

    _ssl_context_built = True
    if not (node_settings.ca_certfile or node_settings.client_certfile):
        _ssl_context = None
        return True

    ctx = ssl.create_default_context(cafile=node_settings.ca_certfile or None)
    if node_settings.client_certfile and node_settings.client_keyfile:
        ctx.load_cert_chain(
            certfile=node_settings.client_certfile,
            keyfile=node_settings.client_keyfile,
        )
    _ssl_context = ctx
    return ctx


def reset_ssl_context() -> None:
    """Test hook: drop the cached context so settings changes take effect."""
    global _ssl_context, _ssl_context_built
    _ssl_context = None
    _ssl_context_built = False


async def invoke_node(
    *,
    endpoint: str,
    model: str,
    prompt: str,
    options: Optional[Dict[str, Any]] = None,
    job_id: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """POST /inference to a node agent.

    Raises NodeUnavailableError for anything that should trigger cloud fallback:
    connection refused, TLS failure, timeout, 503 (node saturated), or any
    other non-2xx.
    """
    # Connecting and generating get separate budgets. Discovering that a node
    # is not there must be fast even when the network blackholes packets
    # instead of refusing politely; generating a long answer on a 3060 is
    # allowed to take its time.
    timeout = httpx.Timeout(
        connect=node_settings.connect_timeout_seconds,
        read=timeout_seconds or node_settings.read_timeout_seconds,
        write=node_settings.write_timeout_seconds,
        pool=node_settings.connect_timeout_seconds,
    )
    url = endpoint.rstrip("/") + "/inference"
    body: Dict[str, Any] = {"model": model, "prompt": prompt, "options": options or {}}
    if job_id:
        body["job_id"] = job_id

    try:
        async with httpx.AsyncClient(verify=build_ssl_context(), timeout=timeout) as client:
            resp = await client.post(url, json=body)
    except httpx.TimeoutException as exc:
        raise NodeUnavailableError(
            "node timed out (connect={}s read={}s): {}".format(
                node_settings.connect_timeout_seconds,
                timeout_seconds or node_settings.read_timeout_seconds,
                type(exc).__name__,
            )
        ) from exc
    except (httpx.HTTPError, ssl.SSLError, OSError) as exc:
        raise NodeUnavailableError("node unreachable: {}".format(exc)) from exc

    if resp.status_code == 503:
        # The agent's own concurrency gate turned us away. Not an error --
        # it is the node correctly telling us to go elsewhere.
        raise NodeUnavailableError("node saturated (503)")
    if resp.status_code >= 400:
        raise NodeUnavailableError("node returned {}: {}".format(resp.status_code, resp.text[:200]))

    try:
        return resp.json()
    except ValueError as exc:
        raise NodeUnavailableError("node returned non-JSON body") from exc
