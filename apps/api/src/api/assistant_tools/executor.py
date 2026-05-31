"""
Tool executor for Goblin Assistant.

Handles the tool-calling loop: when an LLM responds with tool_calls instead
of text, execute each tool via the registry and feed results back until the
LLM produces a final text response.

assistant_tools is the canonical tool system.
"""

from __future__ import annotations

import json
import inspect
import time
from typing import Any, Dict, List, Optional
from contextvars import ContextVar

import structlog

from .contracts import ToolCall
from .registry import get_tool
from api.observability.tool_tracer import tool_tracer
from api.observability.tool_tracer import ToolExecutionStatus

logger = structlog.get_logger(__name__)

# ContextVar for request_id (set by middleware)
_request_id_context: ContextVar[str] = ContextVar("request_id", default="unknown")

# Maximum tool-call rounds to prevent infinite loops
MAX_TOOL_ROUNDS = 5


async def execute_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    runtime_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a single tool call and return the result dict."""
    tool = get_tool(tool_name)
    if tool is None:
        return {"error": f"Unknown tool: {tool_name}"}

    if tool.handler is None:
        return {"error": f"Tool {tool_name} has no handler registered"}

    try:
        call_args = dict(arguments)
        if runtime_context:
            signature = inspect.signature(tool.handler)
            for key, value in runtime_context.items():
                if value is None:
                    continue
                if key in signature.parameters and key not in call_args:
                    call_args[key] = value
        result = await tool.handler(**call_args)
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
        parsed: List[ToolCall] = []
        for item in normalized:
            if not isinstance(item, dict):
                continue
            parsed.append(
                ToolCall(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    arguments=(
                        item.get("arguments", {}) if isinstance(item.get("arguments"), dict) else {}
                    ),
                )
            )
        return parsed or None

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
    """Extract provider-neutral ToolCall contracts from provider response."""
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
    contracts = extract_tool_calls_contract(provider_response)
    if not contracts:
        return None
    return [{"id": call.id, "name": call.name, "arguments": call.arguments} for call in contracts]


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
        messages: Conversation messages (will be mutated with results).
        invoke_fn: async callable matching invoke_provider() signature.
        provider: Provider ID or None for auto.
        model: Model name or None for default.
        tools: OpenAI-format tools list.
        timeout_ms: Per-call timeout.
        user_id: Owning user (used for memory promotion).
        conversation_id: Current conversation (used for memory).

    Returns:
        The final provider response dict (with text, not tool_calls).
        Includes ``visualizations`` key with chart-ready blocks when
        financial tools were executed.
    """
    all_visualizations: List[Dict[str, Any]] = []
    trace_start = time.time()

    # Get request_id from structlog context
    request_id = structlog.contextvars.get_contextvars().get("request_id", "unknown")

    # Start tool execution trace
    trace_id = tool_tracer.start_trace(
        request_id=request_id,
        conversation_id=conversation_id,
        user_id=user_id,
        tool_count=len(tools) if tools else 0,
    )

    loop_error = None

    try:
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
                    resp = dict(response) if isinstance(response, dict) else response
                    if isinstance(resp, dict):
                        resp["visualizations"] = all_visualizations
                        response = resp
                loop_error = "Provider response failed"
                tool_tracer.end_round(trace_id, round_num, error=loop_error)
                break

            tool_calls = extract_tool_calls_contract(response)
            if not tool_calls:
                if all_visualizations:
                    response["visualizations"] = all_visualizations
                tool_tracer.end_round(trace_id, round_num)
                break

            # Start round in tracer
            tool_names = [tc.name for tc in tool_calls or []]
            tool_tracer.start_round(trace_id, round_num, tool_names)

            # Append assistant message with tool_calls
            assistant_message = _assistant_message_from_provider_response(response)
            messages.append(assistant_message)

            # Execute each tool and append results
            for tc in tool_calls or []:
                tool_exec_start = time.time()
                tool_name = tc.name
                args = tc.arguments

                logger.info(
                    "executing_tool_call",
                    tool=tool_name,
                    round=round_num + 1,
                )

                result = await execute_tool_call(
                    tool_name,
                    args,
                    runtime_context={
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                    },
                )
                tool_exec_time = (time.time() - tool_exec_start) * 1000

                # Check for error
                is_error = "error" in result
                status = (
                    ToolExecutionStatus.FAILURE.value
                    if is_error
                    else ToolExecutionStatus.SUCCESS.value
                )

                # Check if visualization was extracted
                viz_extracted = False
                if not is_error:
                    try:
                        from api.services.visualization_service import (
                            extract_visualizations,
                        )

                        viz_blocks = extract_visualizations(
                            tool_name=tool_name,
                            tool_args=args,
                            tool_result=result,
                        )
                        all_visualizations.extend(viz_blocks)
                        viz_extracted = len(viz_blocks) > 0
                    except Exception:
                        logger.debug(
                            "visualization_extraction_skipped",
                            tool=tool_name,
                        )

                # Check if memory was promoted
                memory_promoted = False
                if user_id and not is_error:
                    try:
                        import api.services.tool_result_memory_service

                        service = api.services.tool_result_memory_service
                        extract_and_promote = service.extract_and_promote
                        await extract_and_promote(
                            tool_name=tool_name,
                            tool_args=args,
                            tool_result=result,
                            user_id=user_id,
                            conversation_id=conversation_id,
                        )
                        memory_promoted = True
                    except Exception:
                        logger.debug(
                            "tool_result_promotion_skipped",
                            tool=tool_name,
                        )

                # Record execution in tracer
                result_keys = list(result.keys()) if isinstance(result, dict) else None
                tool_tracer.record_tool_execution(
                    trace_id=trace_id,
                    round_number=round_num,
                    tool_name=tool_name,
                    args_count=len(args),
                    status=status,
                    elapsed_ms=tool_exec_time,
                    result_keys=result_keys,
                    error=result.get("error") if is_error else None,
                    memory_promoted=memory_promoted,
                    visualization_extracted=viz_extracted,
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    }
                )

            # End round
            tool_tracer.end_round(trace_id, round_num)

    except Exception as e:
        loop_error = str(e)
        logger.error("tool_loop_exception", error=loop_error)
        raise

    finally:
        # Exhausted rounds — return last response as-is
        if loop_error is None and round_num >= MAX_TOOL_ROUNDS - 1:
            logger.warning("tool_loop_max_rounds", rounds=MAX_TOOL_ROUNDS)
            loop_error = "Max tool rounds exceeded"

        # End trace
        total_time = (time.time() - trace_start) * 1000

        # Estimate final message tokens (simple approximation)
        final_tokens = sum(len(str(m).split()) for m in messages) * 1.3

        tool_tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=total_time,
            final_message_tokens=int(final_tokens),
            error=loop_error,
        )

        if all_visualizations:
            response["visualizations"] = all_visualizations

    return response
