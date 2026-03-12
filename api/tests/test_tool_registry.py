"""
Tests for tool registry, executor, and the tool-calling loop.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

# Stubs are provided by conftest.py (mock_embedding_service, mock_yfinance)

from api.tools.registry import (
    TOOL_REGISTRY,
    ToolDefinition,
    ToolParameter,
    export_openai_tools,
    get_tool,
    register_tool,
)
from api.tools.executor import (
    execute_tool_call,
    extract_tool_calls,
    run_tool_loop,
)


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestToolRegistry:
    def setup_method(self):
        # Preserve and restore registry across tests
        self._backup = dict(TOOL_REGISTRY)

    def teardown_method(self):
        TOOL_REGISTRY.clear()
        TOOL_REGISTRY.update(self._backup)

    def test_register_and_get(self):
        async def dummy(**kwargs):
            return {"ok": True}

        defn = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter(name="x", type="string", description="input x"),
            ],
            handler=dummy,
        )
        register_tool(defn)
        assert get_tool("test_tool") is defn
        assert get_tool("nonexistent") is None

    def test_openai_schema_export(self):
        async def dummy(**kwargs):
            return {}

        defn = ToolDefinition(
            name="schema_test",
            description="Tests schema export",
            parameters=[
                ToolParameter(name="ticker", type="string", description="Ticker", required=True),
                ToolParameter(name="period", type="string", description="Period", required=False),
            ],
            handler=dummy,
        )
        register_tool(defn)

        schemas = export_openai_tools()
        matching = [s for s in schemas if s["function"]["name"] == "schema_test"]
        assert len(matching) == 1

        func = matching[0]["function"]
        assert func["description"] == "Tests schema export"
        assert "ticker" in func["parameters"]["properties"]
        assert "ticker" in func["parameters"]["required"]
        assert "period" not in func["parameters"]["required"]

    def test_market_data_tools_registered(self):
        """Verify the market_data skill auto-registered its tools."""
        expected = {
            "get_stock_quote",
            "get_price_history",
            "get_financials",
            "get_earnings",
            "get_key_ratios",
        }
        assert expected.issubset(set(TOOL_REGISTRY.keys()))


# ---------------------------------------------------------------------------
# Executor tests
# ---------------------------------------------------------------------------


class TestExecuteToolCall:
    @pytest.mark.asyncio
    async def test_executes_handler(self):
        async def echo_handler(message: str = "") -> dict:
            return {"echo": message}

        defn = ToolDefinition(
            name="_test_echo",
            description="echo",
            parameters=[ToolParameter(name="message", type="string", description="msg")],
            handler=echo_handler,
        )
        backup = dict(TOOL_REGISTRY)
        register_tool(defn)
        try:
            result = await execute_tool_call("_test_echo", {"message": "hello"})
            assert result == {"echo": "hello"}
        finally:
            TOOL_REGISTRY.clear()
            TOOL_REGISTRY.update(backup)

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        result = await execute_tool_call("nonexistent_tool_xyz", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_handler_exception(self):
        async def bad_handler(**kwargs):
            raise RuntimeError("boom")

        defn = ToolDefinition(name="_test_bad", description="bad", handler=bad_handler)
        backup = dict(TOOL_REGISTRY)
        register_tool(defn)
        try:
            result = await execute_tool_call("_test_bad", {})
            assert "error" in result
            assert "boom" in result["error"]
        finally:
            TOOL_REGISTRY.clear()
            TOOL_REGISTRY.update(backup)


# ---------------------------------------------------------------------------
# Extract tool calls
# ---------------------------------------------------------------------------


class TestExtractToolCalls:
    def test_extracts_from_openai_format(self):
        response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [{
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "get_stock_quote",
                                    "arguments": '{"ticker": "AAPL"}',
                                },
                            }],
                        },
                    }],
                },
            },
        }
        calls = extract_tool_calls(response)
        assert calls is not None
        assert len(calls) == 1
        assert calls[0]["name"] == "get_stock_quote"
        assert calls[0]["arguments"] == {"ticker": "AAPL"}

    def test_returns_none_for_text_response(self):
        response = {
            "ok": True,
            "result": {
                "text": "Hello!",
                "raw": {
                    "choices": [{
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "Hello!",
                        },
                    }],
                },
            },
        }
        assert extract_tool_calls(response) is None

    def test_returns_none_for_missing_raw(self):
        assert extract_tool_calls({"ok": True, "result": {"text": "hi"}}) is None

    def test_returns_none_for_error_response(self):
        assert extract_tool_calls({"ok": False, "error": "fail"}) is None


# ---------------------------------------------------------------------------
# Tool loop
# ---------------------------------------------------------------------------


class TestRunToolLoop:
    @pytest.mark.asyncio
    async def test_returns_text_when_no_tools(self):
        """If the first response is text (no tool_calls), return immediately."""
        fake_response = {
            "ok": True,
            "result": {
                "text": "The price is $150.",
                "raw": {
                    "choices": [{
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "The price is $150."},
                    }],
                },
            },
        }

        invoke_fn = AsyncMock(return_value=fake_response)

        result = await run_tool_loop(
            messages=[{"role": "user", "content": "What is AAPL?"}],
            invoke_fn=invoke_fn,
            tools=[{"type": "function", "function": {"name": "get_stock_quote"}}],
        )
        assert result["result"]["text"] == "The price is $150."
        invoke_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_executes_tool_and_returns_final(self):
        """LLM calls a tool → executor runs it → LLM responds with text."""

        # First call: LLM returns tool_calls
        tool_call_response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [{
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "_loop_test_tool",
                                    "arguments": '{"val": "42"}',
                                },
                            }],
                        },
                    }],
                },
            },
        }

        # Second call: LLM returns text
        text_response = {
            "ok": True,
            "result": {
                "text": "The answer is 42.",
                "raw": {
                    "choices": [{
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "The answer is 42."},
                    }],
                },
            },
        }

        invoke_fn = AsyncMock(side_effect=[tool_call_response, text_response])

        # Register a temporary tool
        async def loop_handler(val: str = "") -> dict:
            return {"result": val}

        backup = dict(TOOL_REGISTRY)
        register_tool(ToolDefinition(
            name="_loop_test_tool",
            description="test",
            handler=loop_handler,
        ))

        try:
            messages = [{"role": "user", "content": "test"}]
            result = await run_tool_loop(
                messages=messages,
                invoke_fn=invoke_fn,
                tools=[],
            )
            assert result["result"]["text"] == "The answer is 42."
            assert invoke_fn.call_count == 2

            # Verify tool result was appended to messages
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            assert len(tool_msgs) == 1
            assert json.loads(tool_msgs[0]["content"]) == {"result": "42"}
        finally:
            TOOL_REGISTRY.clear()
            TOOL_REGISTRY.update(backup)
