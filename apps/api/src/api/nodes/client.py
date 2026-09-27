"""mTLS client for talking to a goblin-node-agent.

Every failure mode here is non-fatal by contract: the caller's job is to fall
through to the cloud, so this module raises a single narrow exception type and
never lets an httpx/ssl detail escape into routing code.
"""

from __future__ import annotations

import json
import ssl
from typing import Any, AsyncIterator, Dict, Optional

import httpx
import structlog

from .config import node_settings

logger = structlog.get_logger()


class NodeUnavailableError(RuntimeError):
    """The node could not serve this request. Always recoverable via cloud."""


class NodeSaturatedError(NodeUnavailableError):
    """The node is healthy but has no capacity right now."""


class NodeRequestRejectedError(NodeUnavailableError):
    """The node refused this particular request (4xx), not a health signal.

    A malformed or unsupported request says nothing about whether the node can
    serve the next one, so it must not trip the failure breaker.
    """


class NodeStreamInterruptedError(NodeUnavailableError):
    """A stream failed after tokens were already delivered to the caller.

    Unlike every other error here this one is NOT recoverable by silently
    retrying on the cloud: the caller has already shown part of an answer.
    """


# 4xx statuses that describe the request rather than the node. Auth failures
# (401/403) are deliberately absent: they mean our mTLS or secrets are wrong,
# which will fail every request until someone fixes it.
_REQUEST_SCOPED_STATUSES = {400, 404, 405, 409, 413, 415, 422}


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

    if not (node_settings.ca_certfile or node_settings.client_certfile):
        _ssl_context = None
        _ssl_context_built = True
        return True

    # Only cache once construction succeeds. A missing or unreadable cert must
    # keep failing closed on every call (and pick up the fix once the file
    # appears), never degrade to system trust with no client identity.
    ctx = ssl.create_default_context(cafile=node_settings.ca_certfile or None)
    if node_settings.client_certfile and node_settings.client_keyfile:
        ctx.load_cert_chain(
            certfile=node_settings.client_certfile,
            keyfile=node_settings.client_keyfile,
        )
    _ssl_context = ctx
    _ssl_context_built = True
    return ctx


def reset_ssl_context() -> None:
    """Test hook: drop the cached context so settings changes take effect."""
    global _ssl_context, _ssl_context_built
    _ssl_context = None
    _ssl_context_built = False


def _timeout(timeout_seconds: Optional[float]) -> httpx.Timeout:
    # Connecting and generating get separate budgets. Discovering that a node
    # is not there must be fast even when the network blackholes packets
    # instead of refusing politely; generating a long answer on a 3060 is
    # allowed to take its time.
    return httpx.Timeout(
        connect=node_settings.connect_timeout_seconds,
        read=timeout_seconds or node_settings.read_timeout_seconds,
        write=node_settings.write_timeout_seconds,
        pool=node_settings.connect_timeout_seconds,
    )


def _body(
    model: str, prompt: str, options: Optional[Dict[str, Any]], job_id: Optional[str]
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"model": model, "prompt": prompt, "options": options or {}}
    if job_id:
        body["job_id"] = job_id
    return body


def _raise_for_status(status_code: int, text: str) -> None:
    if status_code in (429, 503):
        # The agent's own concurrency gate turned us away. Not an error --
        # it is the node correctly telling us to go elsewhere.
        raise NodeSaturatedError("node saturated ({})".format(status_code))
    if status_code in _REQUEST_SCOPED_STATUSES:
        raise NodeRequestRejectedError("node rejected request ({}): {}".format(status_code, text))
    if status_code >= 400:
        raise NodeUnavailableError("node returned {}: {}".format(status_code, text))


def _transport_error(exc: BaseException, timeout_seconds: Optional[float]) -> NodeUnavailableError:
    if isinstance(exc, httpx.TimeoutException):
        return NodeUnavailableError(
            "node timed out (connect={}s read={}s): {}".format(
                node_settings.connect_timeout_seconds,
                timeout_seconds or node_settings.read_timeout_seconds,
                type(exc).__name__,
            )
        )
    return NodeUnavailableError("node unreachable: {}".format(exc))


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

    Raises NodeUnavailableError (or a subclass) for anything that should
    trigger cloud fallback: connection refused, TLS failure, timeout, 503
    (node saturated), or any other non-2xx.
    """
    url = endpoint.rstrip("/") + "/inference"
    try:
        # build_ssl_context() is inside the try: a broken cert must surface as
        # a node failure the caller can fall back from, not an escaped OSError.
        async with httpx.AsyncClient(
            verify=build_ssl_context(), timeout=_timeout(timeout_seconds)
        ) as client:
            resp = await client.post(url, json=_body(model, prompt, options, job_id))
    except (httpx.HTTPError, ssl.SSLError, OSError) as exc:
        raise _transport_error(exc, timeout_seconds) from exc

    _raise_for_status(resp.status_code, resp.text[:200])

    try:
        return resp.json()
    except ValueError as exc:
        raise NodeUnavailableError("node returned non-JSON body") from exc


async def stream_node(
    *,
    endpoint: str,
    model: str,
    prompt: str,
    options: Optional[Dict[str, Any]] = None,
    job_id: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """POST /inference/stream and yield the agent's NDJSON events.

    Wire contract (one JSON object per line):
      {"type": "token", "text": "..."}
      {"type": "done", "eval_count": n, "prompt_eval_count": n, "tokens_per_second": f}
      {"type": "error", "error": "..."}

    Errors raised before the first token are ordinary NodeUnavailableError
    subclasses and safe to fall back from. Once a token has been yielded, any
    failure -- transport, an agent "error" event, or the stream ending with no
    "done" -- is NodeStreamInterruptedError.
    """
    url = endpoint.rstrip("/") + "/inference/stream"
    delivered = False

    def _fail(message: str) -> NodeUnavailableError:
        cls = NodeStreamInterruptedError if delivered else NodeUnavailableError
        return cls(message)

    try:
        async with httpx.AsyncClient(
            verify=build_ssl_context(), timeout=_timeout(timeout_seconds)
        ) as client:
            async with client.stream(
                "POST", url, json=_body(model, prompt, options, job_id)
            ) as resp:
                if resp.status_code >= 400:
                    text = (await resp.aread()).decode("utf-8", "replace")[:200]
                    _raise_for_status(resp.status_code, text)

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError as exc:
                        raise _fail("node sent a malformed stream line") from exc
                    if not isinstance(event, dict):
                        raise _fail("node sent a malformed stream event")

                    kind = event.get("type")
                    if kind == "token":
                        text = event.get("text")
                        if isinstance(text, str) and text:
                            delivered = True
                            yield event
                    elif kind == "done":
                        yield event
                        return
                    elif kind == "error":
                        raise _fail("node stream error: {}".format(event.get("error", "unknown")))

                raise _fail("node stream ended without a done event")
    except NodeUnavailableError:
        raise
    except (httpx.HTTPError, ssl.SSLError, OSError) as exc:
        err = _transport_error(exc, timeout_seconds)
        if delivered:
            raise NodeStreamInterruptedError(str(err)) from exc
        raise err from exc
