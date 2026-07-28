"""Provider dispatch stage: invoke, department-chain fallback, tool loop."""

from typing import Any, Dict, Optional

import structlog

from ...assistant_tools.executor import extract_tool_calls_contract, run_tool_loop
from .. import _runtime as _cr
from .rovo_task import create_rovo_task, update_rovo_task
from .stages import resolve_provider_call

logger = structlog.get_logger()

PROVIDER_TIMEOUT_MS = 30000


async def dispatch_with_fallback(
    *,
    resolved_provider: str,
    resolved_department: str,
    pinned_provider: Optional[str],
    model: Optional[str],
    payload: Dict[str, Any],
    fallback_chain: list,
    sanitized_message: str,
    conversation_id: str,
    user_id: str,
    complexity_score: Any,
    intent_meta: dict,
    registered_tools: list,
    messages: list,
) -> tuple[Any, str]:
    """Invoke the selected provider, walking the department fallback chain on
    failure (only when the user didn't pin a provider), then run the tool loop.

    Returns (provider_response, provider_that_answered).
    """
    rovo_task_id = await create_rovo_task(
        resolved_provider,
        sanitized_message,
        conversation_id,
        user_id,
        complexity_score,
        intent_meta,
    )
    provider_response = await resolve_provider_call(
        _cr.invoke_provider(
            pid=resolved_provider,
            model=model,
            payload=payload,
            timeout_ms=PROVIDER_TIMEOUT_MS,
            stream=False,
        )
    )

    # Department chain fallback: when the user didn't pin a provider and the
    # selected one failed, walk the rest of the chain before giving up.
    if (
        not pinned_provider
        and isinstance(provider_response, dict)
        and not provider_response.get("ok", False)
        and "choices" not in provider_response
    ):
        for fallback_pid in fallback_chain:
            if fallback_pid == resolved_provider:
                continue
            logger.warning(
                "chat_department_fallback",
                department=resolved_department,
                failed_provider=resolved_provider,
                fallback_provider=fallback_pid,
                error=str(provider_response.get("error", "unknown")),
            )
            # Don't pin the failed provider's model on the fallback provider.
            fallback_payload = dict(payload)
            fallback_payload.pop("model", None)
            fallback_response = await resolve_provider_call(
                _cr.invoke_provider(
                    pid=fallback_pid,
                    model=None,
                    payload=fallback_payload,
                    timeout_ms=PROVIDER_TIMEOUT_MS,
                    stream=False,
                )
            )
            if isinstance(fallback_response, dict):
                provider_response = fallback_response
                if fallback_response.get("ok", False):
                    resolved_provider = fallback_pid
                    break

    await update_rovo_task(rovo_task_id, provider_response)

    # Tool loop
    if (
        registered_tools
        and isinstance(provider_response, dict)
        and provider_response.get("ok")
        and extract_tool_calls_contract(provider_response)
    ):
        provider_response = await run_tool_loop(
            messages=list(messages),
            invoke_fn=_cr.invoke_provider,
            provider=resolved_provider,
            model=model,
            tools=registered_tools,
            timeout_ms=PROVIDER_TIMEOUT_MS,
            user_id=user_id,
            conversation_id=conversation_id,
        )

    return provider_response, resolved_provider
