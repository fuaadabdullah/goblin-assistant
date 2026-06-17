"""
Tests for tool registry, executor, and the tool-calling loop.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import api.assistant_tools.executor as executor_module
from api.assistant_tools.executor import (
    execute_tool_call,
    extract_tool_calls,
    run_tool_loop,
)

# Stubs are provided by conftest.py (mock_embedding_service, mock_yfinance)
from api.assistant_tools.registry import (
    TOOL_REGISTRY,
    ToolDefinition,
    ToolParameter,
    export_openai_tools,
    export_tool_specs,
    export_tools_for_provider,
    get_tool,
    register_tool,
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

    def test_provider_neutral_tool_specs_export(self):
        specs = export_tool_specs()
        assert isinstance(specs, list)
        assert specs, "Expected at least one registered tool spec"
        first = specs[0]
        assert first.name
        assert isinstance(first.input_schema, dict)

        provider_payload = export_tools_for_provider("anthropic")
        assert isinstance(provider_payload, list)
        assert provider_payload
        assert provider_payload[0].get("type") == "function"

        openai_payload = export_tools_for_provider("openai")
        assert isinstance(openai_payload, list)
        assert openai_payload
        assert openai_payload[0].get("type") == "function"


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
    async def test_injects_runtime_context_and_handles_no_handler_and_typeerror(self):
        seen = {}

        async def contextual_handler(
            *, user_id: str = "", conversation_id: str = "", ticker: str = ""
        ):
            seen["user_id"] = user_id
            seen["conversation_id"] = conversation_id
            seen["ticker"] = ticker
            return {"ok": True}

        backup = dict(TOOL_REGISTRY)
        register_tool(
            ToolDefinition(
                name="_test_contextual",
                description="contextual",
                handler=contextual_handler,
            )
        )
        try:
            result = await execute_tool_call(
                "_test_contextual",
                {"ticker": "AAPL"},
                runtime_context={"user_id": "user-1", "conversation_id": "conv-1"},
            )
            assert result == {"ok": True}
            assert seen == {
                "user_id": "user-1",
                "conversation_id": "conv-1",
                "ticker": "AAPL",
            }
        finally:
            TOOL_REGISTRY.clear()
            TOOL_REGISTRY.update(backup)

        with patch("api.assistant_tools.executor.get_tool") as mock_get:
            mock_get.return_value = type("T", (), {"handler": None})()
            no_handler = await execute_tool_call("missing_handler", {})
            assert "error" in no_handler
            assert "no handler" in no_handler["error"].lower()

        async def raises_type_error(**_kwargs):
            raise TypeError("missing ticker")

        backup = dict(TOOL_REGISTRY)
        register_tool(
            ToolDefinition(
                name="_test_typeerror",
                description="typeerror",
                handler=raises_type_error,
            )
        )
        try:
            typeerror = await execute_tool_call("_test_typeerror", {})
            assert "error" in typeerror
            assert "Invalid arguments" in typeerror["error"]
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

    @pytest.mark.asyncio
    async def test_financial_error_and_runtime_context_branching(self, monkeypatch):
        from api.services.financial_guardrails import FinancialDataError

        seen = {}

        async def financial_handler(
            *, ticker: str = "", user_id: str = "", conversation_id: str = ""
        ) -> dict:
            seen.update(
                {
                    "ticker": ticker,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                }
            )
            raise FinancialDataError("market closed", ticker=ticker)

        backup = dict(TOOL_REGISTRY)
        register_tool(
            ToolDefinition(
                name="_test_financial",
                description="financial",
                handler=financial_handler,
            )
        )
        try:
            result = await execute_tool_call(
                "_test_financial",
                {"ticker": "AAPL", "user_id": "caller-id"},
                runtime_context={
                    "user_id": "runtime-user",
                    "conversation_id": "conv-9",
                    "ignored": None,
                },
            )
            assert result == {"error": "market closed", "ticker": "AAPL"}
            assert seen == {
                "ticker": "AAPL",
                "user_id": "caller-id",
                "conversation_id": "conv-9",
            }
        finally:
            TOOL_REGISTRY.clear()
            TOOL_REGISTRY.update(backup)


# ---------------------------------------------------------------------------
# Extract tool calls
# ---------------------------------------------------------------------------


class TestExtractToolCalls:
    def test_extracts_from_normalized_contract(self):
        response = {
            "ok": True,
            "result": {
                "text": "",
                "tool_calls": [
                    {
                        "id": "tc_normalized_1",
                        "name": "get_stock_quote",
                        "arguments": {"ticker": "MSFT"},
                    }
                ],
            },
        }
        calls = extract_tool_calls(response)
        assert calls is not None
        assert calls[0]["name"] == "get_stock_quote"
        assert calls[0]["arguments"] == {"ticker": "MSFT"}

    def test_extracts_from_openai_format(self):
        response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_abc",
                                        "type": "function",
                                        "function": {
                                            "name": "get_stock_quote",
                                            "arguments": '{"ticker": "AAPL"}',
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                },
            },
        }
        calls = extract_tool_calls(response)
        assert calls is not None
        assert len(calls) == 1
        assert calls[0]["name"] == "get_stock_quote"
        assert calls[0]["arguments"] == {"ticker": "AAPL"}

    def test_extracts_from_anthropic_tool_use_blocks(self):
        response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "anthropic_tool_1",
                            "name": "get_stock_quote",
                            "input": {"ticker": "NVDA"},
                        }
                    ]
                },
            },
        }
        calls = extract_tool_calls(response)
        assert calls is not None
        assert calls[0]["id"] == "anthropic_tool_1"
        assert calls[0]["name"] == "get_stock_quote"
        assert calls[0]["arguments"] == {"ticker": "NVDA"}

    def test_returns_none_for_text_response(self):
        response = {
            "ok": True,
            "result": {
                "text": "Hello!",
                "raw": {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "Hello!",
                            },
                        }
                    ],
                },
            },
        }
        assert extract_tool_calls(response) is None

    def test_returns_none_for_missing_raw(self):
        assert extract_tool_calls({"ok": True, "result": {"text": "hi"}}) is None

    def test_returns_none_for_error_response(self):
        assert extract_tool_calls({"ok": False, "error": "fail"}) is None

    def test_contract_parser_and_assistant_message_variants(self):
        assert executor_module.extract_tool_calls_contract({"result": "nope"}) is None
        assert (
            executor_module.extract_tool_calls_contract(
                {
                    "result": {
                        "tool_calls": [
                            {"id": "tc_1", "name": "normalized", "arguments": {"x": 1}},
                            "ignored",
                        ]
                    }
                }
            )[0].name
            == "normalized"
        )
        anthropic_calls = executor_module.extract_tool_calls_contract(
            {
                "result": {
                    "raw": {
                        "content": [
                            {"type": "text", "text": "hello"},
                            {
                                "type": "tool_use",
                                "id": "anthropic_1",
                                "name": "anthropic_tool",
                                "input": {"ticker": "NVDA"},
                            },
                            "ignored",
                        ]
                    }
                }
            }
        )
        assert anthropic_calls is not None
        assert anthropic_calls[0].id == "anthropic_1"
        openai_calls = executor_module.extract_tool_calls_contract(
            {
                "result": {
                    "raw": {
                        "choices": [
                            {
                                "message": {
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "function": {
                                                "name": "openai_tool",
                                                "arguments": '{"ticker": "AAPL"}',
                                            },
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        )
        assert openai_calls is not None
        assert openai_calls[0].arguments == {"ticker": "AAPL"}
        assert executor_module._assistant_message_from_provider_response(
            {"result": {"raw": {"choices": [{"message": {"role": "assistant", "content": "hi"}}]}}}
        ) == {"role": "assistant", "content": "hi"}
        assert executor_module._assistant_message_from_provider_response(
            {
                "result": {
                    "raw": {
                        "content": [
                            {"type": "text", "text": "A"},
                            {"type": "tool_use", "id": "t1", "name": "ignored"},
                            {"type": "text", "text": "B"},
                        ]
                    }
                }
            }
        ) == {"role": "assistant", "content": "AB"}
        assert executor_module._assistant_message_from_provider_response(
            {"result": {"text": "fallback"}}
        ) == {"role": "assistant", "content": "fallback"}


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
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "The price is $150.",
                            },
                        }
                    ],
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
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "_loop_test_tool",
                                            "arguments": '{"val": "42"}',
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                },
            },
        }

        # Second call: LLM returns text
        text_response = {
            "ok": True,
            "result": {
                "text": "The answer is 42.",
                "raw": {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "The answer is 42.",
                            },
                        }
                    ],
                },
            },
        }

        invoke_fn = AsyncMock(side_effect=[tool_call_response, text_response])

        # Register a temporary tool
        async def loop_handler(val: str = "") -> dict:
            return {"result": val}

        backup = dict(TOOL_REGISTRY)
        register_tool(
            ToolDefinition(
                name="_loop_test_tool",
                description="test",
                handler=loop_handler,
            )
        )

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

    @pytest.mark.asyncio
    async def test_executes_multiple_tool_calls_in_one_round(self):
        """A single tool-call response should execute every requested tool."""
        tool_call_response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "_loop_multi_tool_one",
                                            "arguments": '{"val": "one"}',
                                        },
                                    },
                                    {
                                        "id": "call_2",
                                        "type": "function",
                                        "function": {
                                            "name": "_loop_multi_tool_two",
                                            "arguments": '{"val": "two"}',
                                        },
                                    },
                                ],
                            },
                        }
                    ],
                },
            },
        }

        final_response = {
            "ok": True,
            "result": {
                "text": "Finished.",
                "raw": {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "Finished.",
                            },
                        }
                    ],
                },
            },
        }

        invoke_fn = AsyncMock(side_effect=[tool_call_response, final_response])

        async def tool_one(val: str = "") -> dict:
            return {"tool": "one", "val": val}

        async def tool_two(val: str = "") -> dict:
            return {"tool": "two", "val": val}

        backup = dict(TOOL_REGISTRY)
        register_tool(
            ToolDefinition(
                name="_loop_multi_tool_one",
                description="first",
                handler=tool_one,
            )
        )
        register_tool(
            ToolDefinition(
                name="_loop_multi_tool_two",
                description="second",
                handler=tool_two,
            )
        )

        try:
            messages = [{"role": "user", "content": "run both"}]
            result = await run_tool_loop(messages=messages, invoke_fn=invoke_fn, tools=[])

            assert result["result"]["text"] == "Finished."
            assert invoke_fn.call_count == 2

            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            assert len(tool_msgs) == 2
            assert json.loads(tool_msgs[0]["content"]) == {"tool": "one", "val": "one"}
            assert json.loads(tool_msgs[1]["content"]) == {"tool": "two", "val": "two"}
        finally:
            TOOL_REGISTRY.clear()
            TOOL_REGISTRY.update(backup)

    @pytest.mark.asyncio
    async def test_records_visualizations_and_memory_promotion(self, monkeypatch):
        tool_response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_viz",
                                        "function": {
                                            "name": "_loop_viz_tool",
                                            "arguments": '{"ticker": "MSFT"}',
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            },
        }
        final_response = {
            "ok": True,
            "result": {
                "text": "Done.",
                "raw": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Done.",
                            }
                        }
                    ]
                },
            },
        }

        tool_tracer = executor_module.tool_tracer
        monkeypatch.setattr(tool_tracer, "start_trace", MagicMock(return_value="trace-1"))
        monkeypatch.setattr(tool_tracer, "start_round", MagicMock())
        monkeypatch.setattr(tool_tracer, "end_round", MagicMock())
        monkeypatch.setattr(tool_tracer, "record_tool_execution", MagicMock())
        monkeypatch.setattr(tool_tracer, "end_trace", MagicMock())

        monkeypatch.setattr(
            "api.services.visualization_service.extract_visualizations",
            lambda **_kwargs: [{"kind": "chart"}],
        )
        promote = AsyncMock()
        monkeypatch.setattr(
            "api.services.tool_result_memory_service.extract_and_promote",
            promote,
        )

        async def loop_viz_tool(ticker: str = "", user_id: str = "", conversation_id: str = ""):
            return {"ticker": ticker, "user_id": user_id, "conversation_id": conversation_id}

        backup = dict(TOOL_REGISTRY)
        register_tool(
            ToolDefinition(
                name="_loop_viz_tool",
                description="viz",
                handler=loop_viz_tool,
            )
        )
        invoke_fn = AsyncMock(side_effect=[tool_response, final_response])

        try:
            messages = [{"role": "user", "content": "show chart"}]
            result = await run_tool_loop(
                messages=messages,
                invoke_fn=invoke_fn,
                tools=[{"type": "function", "function": {"name": "_loop_viz_tool"}}],
                user_id="user-7",
                conversation_id="conv-7",
            )

            assert result["result"]["text"] == "Done."
            assert result["visualizations"] == [{"kind": "chart"}]
            assert any(message.get("role") == "tool" for message in messages)
            promote.assert_awaited_once()
            tool_tracer.record_tool_execution.assert_called_once()
            tool_tracer.end_trace.assert_called_once()
        finally:
            TOOL_REGISTRY.clear()
            TOOL_REGISTRY.update(backup)

    @pytest.mark.asyncio
    async def test_provider_failure_and_max_rounds_paths(self, monkeypatch):
        tool_tracer = executor_module.tool_tracer
        monkeypatch.setattr(tool_tracer, "start_trace", MagicMock(return_value="trace-2"))
        monkeypatch.setattr(tool_tracer, "start_round", MagicMock())
        monkeypatch.setattr(tool_tracer, "end_round", MagicMock())
        monkeypatch.setattr(tool_tracer, "record_tool_execution", MagicMock())
        monkeypatch.setattr(tool_tracer, "end_trace", MagicMock())

        failed = await run_tool_loop(
            messages=[{"role": "user", "content": "fail"}],
            invoke_fn=AsyncMock(return_value={"ok": False, "error": "boom"}),
            tools=None,
        )
        assert failed["error"] == "boom"

        tool_response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_repeat",
                                        "function": {
                                            "name": "_loop_repeat_tool",
                                            "arguments": "{}",
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            },
        }

        async def repeat_tool() -> dict:
            return {"ok": True}

        backup = dict(TOOL_REGISTRY)
        register_tool(
            ToolDefinition(
                name="_loop_repeat_tool",
                description="repeat",
                handler=repeat_tool,
            )
        )
        invoke_fn = AsyncMock(side_effect=[tool_response] * executor_module.MAX_TOOL_ROUNDS)

        try:
            result = await run_tool_loop(
                messages=[{"role": "user", "content": "loop"}],
                invoke_fn=invoke_fn,
                tools=[{"type": "function", "function": {"name": "_loop_repeat_tool"}}],
            )

            assert result["ok"] is True
            assert invoke_fn.call_count == executor_module.MAX_TOOL_ROUNDS
            tool_tracer.end_trace.assert_called()
        finally:
            TOOL_REGISTRY.clear()
            TOOL_REGISTRY.update(backup)

    @pytest.mark.asyncio
    async def test_export_tools_for_provider(self):
        """Test exporting tool schemas for a specific provider (e.g., OpenAI)."""
        from api.assistant_tools.registry import export_tools_for_provider

        # Export for OpenAI — should return a list of tool definitions in OpenAI format
        openai_tools = export_tools_for_provider("openai")
        assert isinstance(openai_tools, list)
        # Should have at least some core tools
        assert len(openai_tools) > 0
        # Each tool should have the OpenAI function schema format
        for tool in openai_tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]

    @pytest.mark.asyncio
    async def test_concurrent_tool_invocation(self):
        """Test running multiple tools concurrently in a single loop iteration."""
        tool_tracer = executor_module.tool_tracer

        with (
            patch.object(tool_tracer, "start_trace", return_value="trace-concurrent"),
            patch.object(tool_tracer, "start_round"),
            patch.object(tool_tracer, "end_round"),
            patch.object(tool_tracer, "record_tool_execution"),
            patch.object(tool_tracer, "end_trace"),
        ):
            # Simulate a response with two tool calls (parallel)
            tool_response = {
                "ok": True,
                "result": {
                    "text": "",
                    "raw": {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "function": {
                                                "name": "_concurrent_tool_a",
                                                "arguments": "{}",
                                            },
                                        },
                                        {
                                            "id": "call_2",
                                            "function": {
                                                "name": "_concurrent_tool_b",
                                                "arguments": "{}",
                                            },
                                        },
                                    ],
                                }
                            }
                        ]
                    },
                },
            }

            def tool_a() -> dict:
                return {"result": "tool_a_complete"}

            def tool_b() -> dict:
                return {"result": "tool_b_complete"}

            backup = dict(TOOL_REGISTRY)
            register_tool(
                ToolDefinition(
                    name="_concurrent_tool_a",
                    description="parallel tool a",
                    handler=tool_a,
                )
            )
            register_tool(
                ToolDefinition(
                    name="_concurrent_tool_b",
                    description="parallel tool b",
                    handler=tool_b,
                )
            )

            # Final response with no more tool calls
            final_response = {
                "ok": True,
                "result": {
                    "text": "Both tools completed.",
                    "raw": {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "Both tools completed.",
                                }
                            }
                        ]
                    },
                },
            }

            invoke_fn = AsyncMock(side_effect=[tool_response, final_response])

            try:
                messages = [{"role": "user", "content": "run both tools"}]
                result = await run_tool_loop(
                    messages=messages,
                    invoke_fn=invoke_fn,
                    tools=[
                        {"type": "function", "function": {"name": "_concurrent_tool_a"}},
                        {"type": "function", "function": {"name": "_concurrent_tool_b"}},
                    ],
                )

                assert result["ok"] is True
                assert "Both tools completed" in result["result"]["text"]
                # Verify that both tool calls were recorded (2 invocations in round 1)
                assert tool_tracer.record_tool_execution.call_count >= 2
            finally:
                TOOL_REGISTRY.clear()
                TOOL_REGISTRY.update(backup)
