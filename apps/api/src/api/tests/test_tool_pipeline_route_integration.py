from __future__ import annotations

import json
from contextlib import ExitStack
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth.router import get_current_user
from api.chat_router import router
from api.config.archetypes import DEEP_RESEARCH_CONTRACT, GENERAL_ASSISTANT_CONTRACT


@pytest.fixture
def mock_user():
    return MagicMock(id="user_123", email="test@example.com")


@pytest.fixture
def client(mock_user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


def _payload(response):
    body = response.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def _openai_tool_result(arguments: str, tool_name: str = "get_stock_quote") -> Dict[str, Any]:
    return {
        "ok": True,
        "provider": "openai",
        "model": "gpt-4o-mini",
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
                                        "name": tool_name,
                                        "arguments": arguments,
                                    },
                                }
                            ],
                        },
                    }
                ]
            },
        },
    }


def _anthropic_tool_result(
    input_payload: Dict[str, Any], tool_name: str = "get_stock_quote"
) -> Dict[str, Any]:
    return {
        "ok": True,
        "provider": "anthropic",
        "model": "claude-3-5-haiku-latest",
        "result": {
            "text": "",
            "raw": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "anthropic_tool_1",
                        "name": tool_name,
                        "input": input_payload,
                    }
                ]
            },
        },
    }


def _text_result(provider: str, text: str) -> Dict[str, Any]:
    return {
        "ok": True,
        "provider": provider,
        "model": "test-model",
        "result": {
            "text": text,
            "raw": {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": text,
                        },
                    }
                ]
            },
        },
    }


def _conversation_stub(user_id: str):
    return SimpleNamespace(
        conversation_id="conv_1",
        user_id=user_id,
        messages=[SimpleNamespace(role="user", content="hello")],
    )


def _common_route_patches(mock_user):
    async def fake_require_owned(*_args, **_kwargs):
        return _conversation_stub(mock_user.id)

    mock_wti = MagicMock()
    mock_wti.process_message = AsyncMock(
        return_value={
            "classification": {"type": "working", "confidence": 1.0},
            "decision": {"actions": [], "confidence": 1.0},
            "execution": {"actions_executed": []},
            "processed_at": "2026-05-30T00:00:00.000000",
        }
    )

    return (
        patch("api.chat_router._require_owned_conversation", side_effect=fake_require_owned),
        patch("api.chat_router.messages._get_write_time_intelligence", return_value=mock_wti),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("api.chat_router.messages.schedule_conversation_archive", new_callable=AsyncMock),
        patch("api.chat_router.messages.event_emitter.emit", new_callable=AsyncMock),
    )


def _stacked_patches(mock_user, *extra_patches):
    stack = ExitStack()
    for p in _common_route_patches(mock_user):
        stack.enter_context(p)
    for p in extra_patches:
        stack.enter_context(p)
    return stack


class TestToolPipelineRouteIntegration:
    def test_chat_payload_includes_memory_tool_for_tool_capable_provider(self, client, mock_user):
        seen_tools = {"names": []}

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, timeout_ms, stream
            seen_tools["names"] = [
                item.get("function", {}).get("name")
                for item in payload.get("tools", [])
                if isinstance(item, dict)
            ]
            return _text_result("openai", "ok")

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={"message": "hello", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 200
        assert "memory_recall" in seen_tools["names"]
        assert "create_project" in seen_tools["names"]
        assert "list_projects" in seen_tools["names"]
        assert "get_project_info" in seen_tools["names"]
        assert "create_task" in seen_tools["names"]
        assert "list_tasks" in seen_tools["names"]
        assert "update_task" in seen_tools["names"]
        assert "complete_task" in seen_tools["names"]
        assert "lightweight_research" in seen_tools["names"]
        required = GENERAL_ASSISTANT_CONTRACT.required_tool_names
        assert required.issubset(set(seen_tools["names"]))

    def test_chat_payload_omits_tools_for_non_tool_provider(self, client, mock_user):
        seen_has_tools = {"value": None}

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, timeout_ms, stream
            seen_has_tools["value"] = "tools" in payload
            return _text_result("huggingface", "ok")

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={"message": "hello", "provider": "huggingface", "model": "test-model"},
            )

        assert response.status_code == 200
        assert seen_has_tools["value"] is False

    def test_deep_research_mode_payload_includes_required_tools(self, client, mock_user):
        seen_tools = {"names": []}

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, timeout_ms, stream
            seen_tools["names"] = [
                item.get("function", {}).get("name")
                for item in payload.get("tools", [])
                if isinstance(item, dict)
            ]
            return _text_result("openai", "ok")

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={
                    "message": "research agent check",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "mode": "DEEP_RESEARCH",
                },
            )

        assert response.status_code == 200
        required = DEEP_RESEARCH_CONTRACT.required_tool_names
        assert required.issubset(set(seen_tools["names"]))

    def test_openai_tool_success_promotes_memory(self, client, mock_user):
        mock_exec = AsyncMock(return_value={"ticker": "AAPL", "price": 100.0})
        mock_promote = AsyncMock(return_value=None)

        responses = [
            _openai_tool_result('{"ticker":"AAPL"}'),
            _openai_tool_result('{"ticker":"AAPL"}'),
            _text_result("openai", "AAPL is at 100"),
        ]

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, payload, timeout_ms, stream
            return responses.pop(0)

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
            patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
            patch("api.services.tool_result_memory_service.extract_and_promote", mock_promote),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={"message": "price of AAPL", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 200
        assert _payload(response)["response"] == "AAPL is at 100"
        mock_exec.assert_awaited_once()
        assert mock_exec.await_args.args[0] == "get_stock_quote"
        assert mock_exec.await_args.args[1] == {"ticker": "AAPL"}
        assert mock_exec.await_args.kwargs["runtime_context"]["user_id"] == "user_123"
        assert mock_promote.await_count == 1

    def test_anthropic_tool_success_extracts_tool_use_blocks(self, client, mock_user):
        mock_exec = AsyncMock(return_value={"ticker": "NVDA", "price": 900.0})
        responses = [
            _anthropic_tool_result({"ticker": "NVDA"}),
            _anthropic_tool_result({"ticker": "NVDA"}),
            _text_result("anthropic", "NVDA is at 900"),
        ]

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, payload, timeout_ms, stream
            return responses.pop(0)

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
            patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={
                    "message": "price of NVDA",
                    "provider": "anthropic",
                    "model": "claude-3-5-haiku",
                },
            )

        assert response.status_code == 200
        assert _payload(response)["response"] == "NVDA is at 900"
        mock_exec.assert_awaited_once()
        assert mock_exec.await_args.args[0] == "get_stock_quote"
        assert mock_exec.await_args.args[1] == {"ticker": "NVDA"}

    def test_openai_compatible_providers_cover_gemini_and_groq(self, client, mock_user):
        for provider in ("gemini", "groq"):
            mock_exec = AsyncMock(return_value={"ticker": "MSFT", "price": 400.0})
            responses = [
                _openai_tool_result('{"ticker":"MSFT"}'),
                _openai_tool_result('{"ticker":"MSFT"}'),
                _text_result(provider, f"{provider} tool chain complete"),
            ]

            async def invoke(*, pid, model, payload, timeout_ms, stream=False):
                del pid, model, payload, timeout_ms, stream
                return responses.pop(0)

            with _stacked_patches(
                mock_user,
                patch("api.chat_router.invoke_provider", side_effect=invoke),
                patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
            ):
                response = client.post(
                    "/api/v1/chat/conversations/conv_1/messages",
                    json={"message": "price of MSFT", "provider": provider, "model": "test-model"},
                )

            assert response.status_code == 200
            assert _payload(response)["response"] == f"{provider} tool chain complete"
            mock_exec.assert_awaited_once()
            assert mock_exec.await_args.args[0] == "get_stock_quote"
            assert mock_exec.await_args.args[1] == {"ticker": "MSFT"}

    def test_malformed_tool_arguments_are_safely_coerced(self, client, mock_user):
        mock_exec = AsyncMock(return_value={"error": "Invalid arguments for get_stock_quote"})
        responses = [
            _openai_tool_result('{"ticker":"AAPL"}'),
            _openai_tool_result("{not-valid-json"),
            _text_result("openai", "Handled malformed args"),
        ]

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, payload, timeout_ms, stream
            return responses.pop(0)

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
            patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={"message": "price", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 200
        assert _payload(response)["response"] == "Handled malformed args"
        mock_exec.assert_awaited_once()
        assert mock_exec.await_args.args[0] == "get_stock_quote"
        assert mock_exec.await_args.args[1] == {}

    def test_failed_tool_execution_is_returned_to_loop_and_completes(self, client, mock_user):
        tool_error = {"error": "Tool get_stock_quote failed: timeout"}
        mock_exec = AsyncMock(return_value=tool_error)

        seen_tool_payload = {"content": None}

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, timeout_ms, stream
            idx = invoke.calls
            invoke.calls += 1
            if idx == 2:
                tool_messages = [m for m in payload["messages"] if m.get("role") == "tool"]
                assert tool_messages
                seen_tool_payload["content"] = tool_messages[-1]["content"]
            return [
                _openai_tool_result('{"ticker":"AAPL"}'),
                _openai_tool_result('{"ticker":"AAPL"}'),
                _text_result("openai", "Recovered from tool failure"),
            ][idx]

        invoke.calls = 0

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
            patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={"message": "price", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 200
        assert _payload(response)["response"] == "Recovered from tool failure"
        assert json.loads(seen_tool_payload["content"]) == tool_error

    def test_multi_round_tool_loop_and_no_extra_retry_calls(self, client, mock_user):
        mock_exec = AsyncMock(
            side_effect=[
                {"ticker": "AAPL", "step": 1},
                {"ticker": "AAPL", "step": 2},
            ]
        )

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, payload, timeout_ms, stream
            idx = invoke.calls
            invoke.calls += 1
            responses = [
                _openai_tool_result('{"ticker":"AAPL"}'),
                _openai_tool_result('{"ticker":"AAPL"}'),
                _openai_tool_result('{"ticker":"AAPL"}'),
                _text_result("openai", "Done after two tool rounds"),
            ]
            return responses[idx]

        invoke.calls = 0

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
            patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={"message": "multi", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 200
        assert _payload(response)["response"] == "Done after two tool rounds"
        assert mock_exec.await_count == 2
        # Current behavior only: one initial invoke + two in-loop tool rounds + final text.
        assert invoke.calls == 4

    def test_project_tool_call_executes_in_canonical_route_pipeline(self, client, mock_user):
        mock_exec = AsyncMock(
            return_value={
                "projects": [{"path": "projects/alpha", "name": "Alpha"}],
                "count": 1,
            }
        )
        responses = [
            _openai_tool_result(
                '{"directory":"projects","max_depth":2}', tool_name="list_projects"
            ),
            _openai_tool_result(
                '{"directory":"projects","max_depth":2}', tool_name="list_projects"
            ),
            _text_result("openai", "Found one project"),
        ]

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, payload, timeout_ms, stream
            return responses.pop(0)

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
            patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={"message": "list projects", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 200
        assert _payload(response)["response"] == "Found one project"
        mock_exec.assert_awaited_once()
        assert mock_exec.await_args.args[0] == "list_projects"
        assert mock_exec.await_args.args[1] == {"directory": "projects", "max_depth": 2}

    def test_task_tool_call_executes_in_canonical_route_pipeline(self, client, mock_user):
        mock_exec = AsyncMock(
            return_value={
                "created": True,
                "task": {"task_id": "t1", "title": "Write summary", "status": "pending"},
            }
        )
        responses = [
            _openai_tool_result('{"title":"Write summary"}', tool_name="create_task"),
            _openai_tool_result('{"title":"Write summary"}', tool_name="create_task"),
            _text_result("openai", "Task created"),
        ]

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, payload, timeout_ms, stream
            return responses.pop(0)

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
            patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={"message": "create a task", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 200
        assert _payload(response)["response"] == "Task created"
        mock_exec.assert_awaited_once()
        assert mock_exec.await_args.args[0] == "create_task"
        assert mock_exec.await_args.args[1] == {"title": "Write summary"}

    def test_research_tool_call_executes_in_canonical_route_pipeline(self, client, mock_user):
        mock_exec = AsyncMock(
            return_value={
                "brief": "quick brief",
                "findings": ["one"],
                "sources": [{"title": "S", "url": "https://s.example.com", "source_type": "web"}],
            }
        )
        responses = [
            _openai_tool_result(
                '{"query":"latest battery breakthroughs","max_sources":4}',
                tool_name="lightweight_research",
            ),
            _openai_tool_result(
                '{"query":"latest battery breakthroughs","max_sources":4}',
                tool_name="lightweight_research",
            ),
            _text_result("openai", "Research complete"),
        ]

        async def invoke(*, pid, model, payload, timeout_ms, stream=False):
            del pid, model, payload, timeout_ms, stream
            return responses.pop(0)

        with _stacked_patches(
            mock_user,
            patch("api.chat_router.invoke_provider", side_effect=invoke),
            patch("api.assistant_tools.executor.execute_tool_call", mock_exec),
        ):
            response = client.post(
                "/api/v1/chat/conversations/conv_1/messages",
                json={
                    "message": "research battery breakthroughs",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            )

        assert response.status_code == 200
        assert _payload(response)["response"] == "Research complete"
        mock_exec.assert_awaited_once()
        assert mock_exec.await_args.args[0] == "lightweight_research"
        assert mock_exec.await_args.args[1] == {
            "query": "latest battery breakthroughs",
            "max_sources": 4,
        }
