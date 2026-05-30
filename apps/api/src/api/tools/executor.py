"""
Tool executor for Goblin Assistant.

Handles the tool-calling loop: when an LLM responds with tool_calls instead
of text, execute each tool via the registry and feed results back until the
LLM produces a final text response.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import structlog

from .contracts import ToolCall
from .registry import get_tool

logger = structlog.get_logger(__name__)

# Maximum tool-call rounds to prevent infinite loops
MAX_TOOL_ROUNDS = 5
DEFAULT_TOOL_MAX_RETRIES = 2


async def execute_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a single tool call and return the result dict."""
    tool = get_tool(tool_name)
    if tool is None:
        return {"error": f"Unknown tool: {tool_name}"}

    if tool.handler is None:
        return {"error": f"Tool {tool_name} has no handler registered"}

    try:
        result = await tool.handler(**arguments)
        return result
    except TypeError as e:
        logger.warning("tool_argument_error", tool=tool_name, error=str(e))
        return {"error": f"Invalid arguments for {tool_name}: {e}"}
    except Exception as e:
        # Import guardrail errors for cleaner messages
        try:
            from api.services.financial_guardrails import FinancialDataError

            if isinstance(e, FinancialDataError):
                logger.warning("tool_financial_error", tool=tool_name, error=str(e))
                return e.to_dict()
        except ImportError:
            pass
        logger.error("tool_execution_error", tool=tool_name, error=str(e))
        return {"error": f"Tool {tool_name} failed: {e}"}


def _is_transient_error(error_msg: Optional[str]) -> bool:
    """Return True when an error appears retryable."""
    if not error_msg:
        return False
    transient_markers = (
        "timeout",
        "timed out",
        "connection",
        "rate limit",
        "temporarily unavailable",
        "service unavailable",
        "too many requests",
        "503",
        "429",
    )
    normalized = error_msg.lower()
    return any(marker in normalized for marker in transient_markers)


async def execute_tool_call_with_retry(
    tool_name: str,
    arguments: Dict[str, Any],
    max_retries: int = DEFAULT_TOOL_MAX_RETRIES,
) -> Dict[str, Any]:
    """Execute a tool call with retry/backoff for transient failures."""
    retries = max(1, max_retries)
    for attempt in range(retries):
        result = await execute_tool_call(tool_name, arguments)
        error_msg = result.get("error")
        if not error_msg:
            return result

        should_retry = attempt < retries - 1 and _is_transient_error(str(error_msg))
        if not should_retry:
            return result

        backoff_seconds = 0.5 * (2**attempt)
        logger.warning(
            "tool_execution_retry",
            tool=tool_name,
            attempt=attempt + 1,
            max_retries=retries,
            backoff_seconds=backoff_seconds,
            error=str(error_msg),
        )
        await asyncio.sleep(backoff_seconds)

    return {"error": f"Tool {tool_name} exhausted retries"}


def _parse_openai_compat_tool_calls(raw_calls: List[Dict[str, Any]]) -> List[ToolCall]:
    parsed: List[ToolCall] = []
    for call in raw_calls:
        func = call.get("function", {})
        args_raw = func.get("arguments", "{}")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except json.JSONDecodeError:
            args = {}
        parsed.append(
            ToolCall(
                id=str(call.get("id", "")),
                name=str(func.get("name", "")),
                arguments=args if isinstance(args, dict) else {},
            )
        )
    return parsed


def _extract_tool_calls_from_result(
    result: Dict[str, Any],
) -> Optional[List[ToolCall]]:
    normalized = result.get("tool_calls")
    if isinstance(normalized, list):
        calls: List[ToolCall] = []
        for item in normalized:
            if not isinstance(item, dict):
                continue
            calls.append(
                ToolCall(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    arguments=(
                        item.get("arguments", {}) if isinstance(item.get("arguments"), dict) else {}
                    ),
                )
            )
        return calls or None

    raw = result.get("raw", {})
    if not isinstance(raw, dict):
        return None

    content_blocks = raw.get("content")
    if isinstance(content_blocks, list):
        anthropic_calls: List[ToolCall] = []
        for idx, block in enumerate(content_blocks):
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            anthropic_calls.append(
                ToolCall(
                    id=str(block.get("id", f"anthropic_tool_{idx}")),
                    name=str(block.get("name", "")),
                    arguments=(
                        block.get("input", {}) if isinstance(block.get("input"), dict) else {}
                    ),
                )
            )
        if anthropic_calls:
            return anthropic_calls

    choices = raw.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0] if isinstance(choices[0], dict) else {}
    message = first_choice.get("message", {}) if isinstance(first_choice, dict) else {}
    if not isinstance(message, dict):
        return None
    tool_calls = message.get("tool_calls", [])
    if not isinstance(tool_calls, list) or not tool_calls:
        return None
    return _parse_openai_compat_tool_calls(tool_calls) or None


def extract_tool_calls_contract(
    provider_response: Dict[str, Any],
) -> Optional[List[ToolCall]]:
    """Extract provider-neutral tool call contracts from response payload."""
    try:
        result = provider_response.get("result", {})
        if not isinstance(result, dict):
            return None
        return _extract_tool_calls_from_result(result)
    except (KeyError, IndexError, TypeError):
        return None


def extract_tool_calls(
    provider_response: Dict[str, Any],
) -> Optional[List[Dict[str, Any]]]:
    """Backward-compatible dict form of extracted tool calls."""
    calls = extract_tool_calls_contract(provider_response)
    if not calls:
        return None
    return [{"id": call.id, "name": call.name, "arguments": call.arguments} for call in calls]


def _assistant_message_from_provider_response(
    provider_response: Dict[str, Any],
) -> Dict[str, Any]:
    result = provider_response.get("result", {})
    if not isinstance(result, dict):
        return {"role": "assistant", "content": ""}

    raw = result.get("raw", {})
    if isinstance(raw, dict):
        choices = raw.get("choices", [])
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                return message
        content_blocks = raw.get("content")
        if isinstance(content_blocks, list):
            text_parts = [
                block.get("text", "")
                for block in content_blocks
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            return {
                "role": "assistant",
                "content": "".join(text_parts),
            }

    return {"role": "assistant", "content": str(result.get("text", ""))}


async def run_tool_loop(
    messages: List[Dict[str, Any]],
    invoke_fn,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    timeout_ms: int = 30_000,
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the tool-calling loop until we get a text response.

    Args:
        messages: Conversation messages (will be mutated with tool results).
        invoke_fn: async callable matching invoke_provider() signature.
        provider: Provider ID or None for auto.
        model: Model name or None for default.
        tools: OpenAI-format tools list.
        timeout_ms: Per-call timeout.
        user_id: Owning user (used for memory promotion).
        conversation_id: Current conversation (used for memory promotion).

    Returns:
        The final provider response dict (with text, not tool_calls).
        Includes ``visualizations`` key with chart-ready blocks when
        financial tools were executed.
    """
    all_visualizations: List[Dict[str, Any]] = []

    for round_num in range(MAX_TOOL_ROUNDS):
        payload: Dict[str, Any] = {"messages": messages, "model": model}
        if tools:
            payload["tools"] = tools

        response = await invoke_fn(
            pid=provider,
            model=model,
            payload=payload,
            timeout_ms=timeout_ms,
            stream=False,
        )

        if not isinstance(response, dict) or not response.get("ok"):
            if all_visualizations:
                response = dict(response) if isinstance(response, dict) else response
                if isinstance(response, dict):
                    response["visualizations"] = all_visualizations
            return response

        tool_calls = extract_tool_calls_contract(response)
        if not tool_calls:
            if all_visualizations:
                response["visualizations"] = all_visualizations
            return response

        # Append assistant message with tool_calls
        assistant_message = _assistant_message_from_provider_response(response)
        messages.append(assistant_message)

        # Execute each tool and append results
        for tc in tool_calls:
            logger.info(
                "executing_tool_call",
                tool=tc.name,
                round=round_num + 1,
            )
            result = await execute_tool_call_with_retry(tc.name, tc.arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                }
            )

            # Extract chart-ready visualizations (fire-and-forget)
            if "error" not in result:
                try:
                    from api.services.visualization_service import (
                        extract_visualizations,
                    )

                    viz_blocks = extract_visualizations(
                        tool_name=tc.name,
                        tool_args=tc.arguments,
                        tool_result=result,
                    )
                    all_visualizations.extend(viz_blocks)
                except Exception:
                    logger.debug("visualization_extraction_skipped", tool=tc.name)

            # Promote extractable financial facts to memory (fire-and-forget)
            if user_id and "error" not in result:
                try:
                    from api.services.tool_result_memory_service import (
                        extract_and_promote,
                    )

                    await extract_and_promote(
                        tool_name=tc.name,
                        tool_args=tc.arguments,
                        tool_result=result,
                        user_id=user_id,
                        conversation_id=conversation_id,
                    )
                except Exception:
                    logger.debug("tool_result_promotion_skipped", tool=tc.name)

    # Exhausted rounds — return last response as-is
    logger.warning("tool_loop_max_rounds", rounds=MAX_TOOL_ROUNDS)
    if all_visualizations:
        response["visualizations"] = all_visualizations
    return response
