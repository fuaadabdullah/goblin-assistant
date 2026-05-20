"""
Tool executor for Goblin Assistant.

Handles the tool-calling loop: when an LLM responds with tool_calls instead
of text, execute each tool via the registry and feed results back until the
LLM produces a final text response.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import structlog

from .registry import get_tool

logger = structlog.get_logger(__name__)

# Maximum tool-call rounds to prevent infinite loops
MAX_TOOL_ROUNDS = 5


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


def extract_tool_calls(provider_response: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Extract tool_calls from a provider response, if present.

    Supports OpenAI-format responses where tool calls live at:
    - response["result"]["raw"]["choices"][0]["message"]["tool_calls"]
    """
    try:
        raw = provider_response.get("result", {}).get("raw", {})
        choices = raw.get("choices", [])
        if not choices:
            return None

        message = choices[0].get("message", {})
        finish_reason = choices[0].get("finish_reason")

        if finish_reason not in ("tool_calls", "stop") and message.get("tool_calls"):
            return _parse_tool_calls(message["tool_calls"]) or None

        if finish_reason == "tool_calls" or message.get("tool_calls"):
            return _parse_tool_calls(message.get("tool_calls", [])) or None

        return None
    except (KeyError, IndexError, TypeError):
        return None


def _parse_tool_calls(raw_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize tool call objects."""
    parsed = []
    for call in raw_calls:
        func = call.get("function", {})
        args_raw = func.get("arguments", "{}")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except json.JSONDecodeError:
            args = {}

        parsed.append({
            "id": call.get("id", ""),
            "name": func.get("name", ""),
            "arguments": args,
        })
    return parsed


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

        tool_calls = extract_tool_calls(response)
        if not tool_calls:
            if all_visualizations:
                response["visualizations"] = all_visualizations
            return response

        # Append assistant message with tool_calls
        raw = response.get("result", {}).get("raw", {})
        assistant_message = raw.get("choices", [{}])[0].get("message", {})
        messages.append(assistant_message)

        # Execute each tool and append results
        for tc in tool_calls:
            logger.info(
                "executing_tool_call",
                tool=tc["name"],
                round=round_num + 1,
            )
            result = await execute_tool_call(tc["name"], tc["arguments"])
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, default=str),
            })

            # Extract chart-ready visualizations (fire-and-forget)
            if "error" not in result:
                try:
                    from api.services.visualization_service import (
                        extract_visualizations,
                    )
                    viz_blocks = extract_visualizations(
                        tool_name=tc["name"],
                        tool_args=tc["arguments"],
                        tool_result=result,
                    )
                    all_visualizations.extend(viz_blocks)
                except Exception:
                    logger.debug("visualization_extraction_skipped", tool=tc["name"])

            # Promote extractable financial facts to memory (fire-and-forget)
            if user_id and "error" not in result:
                try:
                    from api.services.tool_result_memory_service import (
                        extract_and_promote,
                    )
                    await extract_and_promote(
                        tool_name=tc["name"],
                        tool_args=tc["arguments"],
                        tool_result=result,
                        user_id=user_id,
                        conversation_id=conversation_id,
                    )
                except Exception:
                    logger.debug("tool_result_promotion_skipped", tool=tc["name"])

    # Exhausted rounds — return last response as-is
    logger.warning("tool_loop_max_rounds", rounds=MAX_TOOL_ROUNDS)
    if all_visualizations:
        response["visualizations"] = all_visualizations
    return response
