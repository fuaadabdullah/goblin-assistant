"""The local-compute tier.

This is deliberately NOT a provider. Providers are interchangeable vendor
endpoints ranked against each other on cost and latency; nodes are machines we
own, with capacity, residency and health that the provider abstraction has no
vocabulary for. Modelling node-001..node-N as fifteen pseudo-providers would
pollute every cost calculation and ranking decision in the router.

So the shape is:

    route_task
      |-- local compute  -> NodeRegistry -> node-001
      `-- cloud ladder   -> Groq / DeepSeek / Gemini / ...

Local is attempted first and, on any failure at all, returns None so the caller
proceeds down the existing cloud ladder untouched.

Semantics the router can rely on:

* Cost: local work is billed at $0.00 with real token counts from the node
  (``usage``), in the same shape cloud providers report.
* Failure: every eligible node is tried in load order before falling back.
  Transport/5xx failures feed the node's breaker; 503/429 (saturation) and
  request-scoped 4xx do not, because they say nothing about node health.
* Streaming: a stream only counts as served once the first token arrives, so
  a node that dies before speaking falls back to the cloud invisibly. After
  the first token, failure surfaces to the caller as an interrupted stream --
  splicing a cloud answer onto half a local one would be worse.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import structlog

from .client import (
    NodeRequestRejectedError,
    NodeSaturatedError,
    NodeStreamInterruptedError,
    NodeUnavailableError,
    invoke_node,
    stream_node,
)
from .config import node_settings
from .endpoint_policy import InvalidEndpointError, validate_endpoint
from .models import NodeRecord
from .registry import NodeRegistry, Reservation, node_registry

logger = structlog.get_logger()

# Task types that a local inference node can serve. Anything else (embeddings,
# vision, tool-use) goes straight to the cloud until a node advertises it.
LOCAL_CAPABLE_TASKS = {"chat", "generate", "completion", "text", "general"}


def _extract_prompt(payload: Dict[str, Any]) -> Optional[str]:
    """Pull a plain prompt out of the several shapes callers use."""
    prompt = payload.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt

    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        parts = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                role = message.get("role", "user")
                parts.append("{}: {}".format(role, content) if role != "user" else content)
        if parts:
            return "\n\n".join(parts)

    task = payload.get("task")
    if isinstance(task, str) and task.strip():
        return task
    return None


def _usage(result: Dict[str, Any]) -> Dict[str, int]:
    prompt_tokens = result.get("prompt_eval_count")
    completion_tokens = result.get("eval_count")
    usage: Dict[str, int] = {}
    if isinstance(prompt_tokens, int):
        usage["prompt_tokens"] = prompt_tokens
    if isinstance(completion_tokens, int):
        usage["completion_tokens"] = completion_tokens
    if usage:
        usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    return usage


def _prepare(
    task_type: str, payload: Dict[str, Any], reg: NodeRegistry
) -> Optional[Tuple[str, str, List[NodeRecord], Optional[Dict[str, Any]]]]:
    """Common gatekeeping: returns (prompt, model, candidates, options) or None."""
    if not node_settings.enabled:
        return None
    if task_type not in LOCAL_CAPABLE_TASKS:
        return None

    prompt = _extract_prompt(payload)
    if not prompt:
        return None

    requested_model = payload.get("model")
    model = requested_model if isinstance(requested_model, str) and requested_model else None

    # A node must actually host the requested model. When the caller named no
    # model we look for the configured default rather than sending work to a
    # node and hoping.
    wanted = model or node_settings.default_model
    candidates = reg.eligible_nodes(model=wanted)
    if not candidates:
        logger.debug("local_compute_skipped", reason="no_eligible_node", model=wanted)
        return None
    options = payload.get("options") if isinstance(payload.get("options"), dict) else None
    return prompt, wanted, candidates, options


def _claim(node: NodeRecord, wanted: str, reg: NodeRegistry) -> Optional[Tuple[str, Reservation]]:
    """Validate a candidate's endpoint and reserve a slot. None means skip it."""
    if not node.endpoint:
        # Registered but unreachable: it never told us where it lives.
        logger.warning("local_compute_skipped", reason="no_endpoint", node_id=node.node_id)
        return None

    # Re-validate at dispatch time, not just at registration. Policy can be
    # tightened (an allowlist added) while nodes registered under the looser
    # rules are still resident in the registry.
    try:
        target = validate_endpoint(node.endpoint)
    except InvalidEndpointError as exc:
        logger.warning(
            "local_compute_skipped",
            reason="endpoint_rejected",
            node_id=node.node_id,
            error=str(exc),
        )
        return None

    # eligible_nodes() is a snapshot. Reserve atomically before dialing so two
    # requests cannot both observe the final free slot between heartbeats.
    reservation = reg.try_reserve(node.node_id, model=wanted)
    if reservation is None:
        logger.debug(
            "local_compute_skipped",
            reason="capacity_changed",
            node_id=node.node_id,
            model=wanted,
        )
        return None
    return target, reservation


def _note_failure(
    reg: NodeRegistry, node: NodeRecord, exc: NodeUnavailableError, job_id: str
) -> None:
    """Classify a pre-delivery failure: only real node faults feed the breaker."""
    if isinstance(exc, NodeSaturatedError):
        reason = "saturated"
    elif isinstance(exc, NodeRequestRejectedError):
        reason = "request_rejected"
    else:
        reason = "unavailable"
        reg.record_failure(node.node_id)
    logger.info(
        "local_compute_fallback",
        node_id=node.node_id,
        reason=reason,
        error=str(exc),
        job_id=job_id,
    )


def _served(
    node: NodeRecord,
    wanted: str,
    *,
    text: str,
    latency_ms: float,
    usage: Dict[str, int],
    tokens_per_second: Any,
) -> Dict[str, Any]:
    # Shaped to match what cloud providers return, so downstream consumers
    # (_extract_result_text and friends) need no special-casing. `text` is
    # duplicated at both levels because both readers exist in this codebase.
    provider = "local:{}".format(node.node_id)
    return {
        "ok": True,
        "text": text,
        "result": {"text": text, "usage": usage, "cost_usd": 0.0},
        "provider": provider,
        "model": wanted,
        "selected_provider": provider,
        "compute_tier": "local",
        "node_id": node.node_id,
        "latency_ms": round(latency_ms, 2),
        "usage": usage,
        # Hardware we own: the marginal cost of a local generation is zero.
        "cost_usd": 0.0,
        "tokens_per_second": tokens_per_second,
        "eval_count": usage.get("completion_tokens"),
    }


async def try_local_compute(
    task_type: str,
    payload: Dict[str, Any],
    *,
    registry: Optional[NodeRegistry] = None,
    request_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Attempt to serve this request on a self-hosted node.

    Returns a provider-shaped success dict, or None meaning "not served here"
    -- which is the signal for the caller to use the cloud ladder. None is
    returned for every negative case (disabled, no eligible node, unsupported
    model, every node failed), because from the router's perspective they are
    all the same instruction: go to the cloud.
    """
    reg = registry or node_registry
    prepared = _prepare(task_type, payload, reg)
    if prepared is None:
        return None
    prompt, wanted, candidates, options = prepared

    job_id = request_id or str(uuid.uuid4())
    for node in candidates:
        claim = _claim(node, wanted, reg)
        if claim is None:
            continue
        target, reservation = claim

        started = time.perf_counter()
        try:
            result = await invoke_node(
                endpoint=target,
                model=wanted,
                prompt=prompt,
                options=options,
                job_id=job_id,
            )
        except NodeUnavailableError as exc:
            _note_failure(reg, node, exc, job_id)
            continue
        finally:
            reg.release(node.node_id, reservation)

        reg.record_success(node.node_id)
        latency_ms = (time.perf_counter() - started) * 1000
        usage = _usage(result)
        logger.info(
            "local_compute_served",
            node_id=node.node_id,
            model=wanted,
            job_id=job_id,
            latency_ms=round(latency_ms, 2),
            tokens_per_second=result.get("tokens_per_second"),
        )
        return _served(
            node,
            wanted,
            text=result.get("response", ""),
            latency_ms=latency_ms,
            usage=usage,
            tokens_per_second=result.get("tokens_per_second"),
        )
    return None


async def try_local_compute_stream(
    task_type: str,
    payload: Dict[str, Any],
    *,
    registry: Optional[NodeRegistry] = None,
    request_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Streaming counterpart of try_local_compute.

    Returns ``{"ok": True, "stream": <async gen of {"text": ...}>, ...}`` once
    a node has produced its first token, or None to fall back to the cloud.
    The node's reservation is held until the stream is exhausted or closed.

    Chunks match the cloud providers' ``{"text": ...}`` shape. The final chunk
    is ``{"text": "", "done": True, "usage": {...}, "cost_usd": 0.0}``, which
    existing consumers skip as empty text. A failure after the first token
    raises NodeStreamInterruptedError from the generator.
    """
    reg = registry or node_registry
    if not node_settings.streaming_enabled:
        return None
    prepared = _prepare(task_type, payload, reg)
    if prepared is None:
        return None
    prompt, wanted, candidates, options = prepared

    job_id = request_id or str(uuid.uuid4())
    for node in candidates:
        claim = _claim(node, wanted, reg)
        if claim is None:
            continue
        target, reservation = claim

        started = time.perf_counter()
        events = stream_node(
            endpoint=target,
            model=wanted,
            prompt=prompt,
            options=options,
            job_id=job_id,
        )
        try:
            first = await events.__anext__()
        except StopAsyncIteration:
            reg.release(node.node_id, reservation)
            _note_failure(reg, node, NodeUnavailableError("empty stream"), job_id)
            continue
        except NodeUnavailableError as exc:
            reg.release(node.node_id, reservation)
            _note_failure(reg, node, exc, job_id)
            continue
        except BaseException:
            reg.release(node.node_id, reservation)
            raise

        first_token_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "local_compute_stream_started",
            node_id=node.node_id,
            model=wanted,
            job_id=job_id,
            first_token_ms=round(first_token_ms, 2),
        )
        return {
            "ok": True,
            "stream": _LocalStream(reg, node, reservation, first, events, job_id=job_id),
            "provider": "local:{}".format(node.node_id),
            "selected_provider": "local:{}".format(node.node_id),
            "model": wanted,
            "compute_tier": "local",
            "node_id": node.node_id,
            "latency_ms": round(first_token_ms, 2),
            "cost_usd": 0.0,
        }
    return None


def _chunk(event: Dict[str, Any]) -> Dict[str, Any]:
    """Translate one agent event into a provider-shaped chunk."""
    if event.get("type") == "done":
        return {
            "text": "",
            "done": True,
            "usage": _usage(event),
            "cost_usd": 0.0,
            "tokens_per_second": event.get("tokens_per_second"),
        }
    return {"text": event.get("text", "")}


class _LocalStream:
    """Async iterator over a node stream that owns the node's reservation.

    A class rather than an async generator on purpose: closing a generator
    that was never iterated skips its ``finally``, which would leak the slot
    whenever a caller bails out before reading. Here the reservation is
    released exactly once -- on exhaustion, on error, on aclose(), or as a
    last resort when the object is collected.
    """

    def __init__(
        self,
        reg: NodeRegistry,
        node: NodeRecord,
        reservation: Reservation,
        first: Dict[str, Any],
        events: AsyncIterator[Dict[str, Any]],
        *,
        job_id: str,
    ) -> None:
        self._reg = reg
        self._node = node
        self._reservation = reservation
        self._pending: Optional[Dict[str, Any]] = first
        self._events = events
        self._job_id = job_id
        self._finished = False

    def __aiter__(self) -> "_LocalStream":
        return self

    async def __anext__(self) -> Dict[str, Any]:
        if self._finished:
            raise StopAsyncIteration
        if self._pending is not None:
            event, self._pending = self._pending, None
        else:
            try:
                event = await self._events.__anext__()
            except StopAsyncIteration:
                await self._finish(ok=True)
                raise
            except NodeStreamInterruptedError as exc:
                logger.warning(
                    "local_compute_stream_interrupted",
                    node_id=self._node.node_id,
                    job_id=self._job_id,
                    error=str(exc),
                )
                await self._finish(ok=False)
                raise
            except BaseException:
                await self._finish(ok=None)
                raise
        if event.get("type") == "done":
            await self._finish(ok=True)
        return _chunk(event)

    async def aclose(self) -> None:
        await self._finish(ok=None)

    async def _finish(self, *, ok: Optional[bool]) -> None:
        if self._finished:
            return
        self._finished = True
        self._reg.release(self._node.node_id, self._reservation)
        if ok is True:
            self._reg.record_success(self._node.node_id)
        elif ok is False:
            self._reg.record_failure(self._node.node_id)
        aclose = getattr(self._events, "aclose", None)
        if aclose is not None:
            await aclose()

    def __del__(self) -> None:
        if not self._finished:
            self._finished = True
            self._reg.release(self._node.node_id, self._reservation)
