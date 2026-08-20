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
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

import structlog

from .client import NodeUnavailableError, invoke_node
from .config import node_settings
from .endpoint_policy import InvalidEndpointError, validate_endpoint
from .registry import NodeRegistry, node_registry

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
    model, node failure), because from the router's perspective they are all
    the same instruction: go to the cloud.
    """
    reg = registry or node_registry

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

    node = candidates[0]
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

    job_id = request_id or str(uuid.uuid4())
    started = time.perf_counter()
    try:
        result = await invoke_node(
            endpoint=target,
            model=wanted,
            prompt=prompt,
            options=payload.get("options") if isinstance(payload.get("options"), dict) else None,
            job_id=job_id,
        )
    except NodeUnavailableError as exc:
        reg.record_failure(node.node_id)
        logger.info(
            "local_compute_fallback",
            node_id=node.node_id,
            reason=str(exc),
            job_id=job_id,
        )
        return None

    reg.record_success(node.node_id)
    latency_ms = (time.perf_counter() - started) * 1000
    text = result.get("response", "")

    logger.info(
        "local_compute_served",
        node_id=node.node_id,
        model=wanted,
        job_id=job_id,
        latency_ms=round(latency_ms, 2),
        tokens_per_second=result.get("tokens_per_second"),
    )

    # Shaped to match what cloud providers return, so downstream consumers
    # (_extract_result_text and friends) need no special-casing. `text` is
    # duplicated at both levels because both readers exist in this codebase.
    return {
        "ok": True,
        "text": text,
        "result": {"text": text},
        "provider": "local:{}".format(node.node_id),
        "model": wanted,
        "selected_provider": "local:{}".format(node.node_id),
        "compute_tier": "local",
        "node_id": node.node_id,
        "latency_ms": round(latency_ms, 2),
        "tokens_per_second": result.get("tokens_per_second"),
        "eval_count": result.get("eval_count"),
    }
