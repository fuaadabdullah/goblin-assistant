"""Tests for capability permission gate in executor."""

from unittest.mock import AsyncMock, patch

import pytest

from api.assistant_tools.executor import execute_tool_call
from api.assistant_tools.registry import TOOL_REGISTRY, ToolDefinition
from api.capabilities.models import Capability, CapabilityType
from api.capabilities.registry import capability_registry


@pytest.fixture(autouse=True)
def setup_test_tool():
    """Register a test tool and capability."""
    tool_def = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters=[],
        handler=AsyncMock(return_value={"result": "success"}),
        category="testing",
    )
    TOOL_REGISTRY["test_tool"] = tool_def

    cap = Capability(
        id="test_cap",
        type=CapabilityType.TOOL,
        name="Test Capability",
        description="Test",
        tool_names=["test_tool"],
        requires_explicit_grant=True,
    )
    capability_registry.register(cap)

    yield

    TOOL_REGISTRY.pop("test_tool", None)
    capability_registry._capabilities.pop("test_cap", None)
    capability_registry._tool_to_cap.pop("test_tool", None)


@pytest.mark.asyncio
class TestExecutorCapabilityGate:
    async def test_execute_tool_no_user_context(self):
        """Tool execution without user_id should skip permission check."""
        result = await execute_tool_call("test_tool", {}, runtime_context={})
        assert result["result"] == "success"

    async def test_execute_tool_unknown_tool(self):
        """Unknown tool should return error."""
        result = await execute_tool_call("unknown_tool", {}, runtime_context={"user_id": "user1"})
        assert "error" in result
        assert "Unknown tool" in result["error"]

    async def test_execute_tool_no_handler(self):
        """Tool without handler should return error."""
        tool_def = ToolDefinition(
            name="no_handler_tool",
            description="No handler",
            parameters=[],
            handler=None,
            category="testing",
        )
        TOOL_REGISTRY["no_handler_tool"] = tool_def

        result = await execute_tool_call(
            "no_handler_tool", {}, runtime_context={"user_id": "user1"}
        )
        assert "error" in result
        assert "has no handler" in result["error"]

        TOOL_REGISTRY.pop("no_handler_tool", None)

    async def test_execute_tool_unregistered_tool_no_capability(self):
        """Tool not in any capability should execute without capability check."""
        tool_def = ToolDefinition(
            name="unregistered_tool",
            description="Not in any capability",
            parameters=[],
            handler=AsyncMock(return_value={"result": "unregistered"}),
            category="testing",
        )
        TOOL_REGISTRY["unregistered_tool"] = tool_def

        result = await execute_tool_call(
            "unregistered_tool", {}, runtime_context={"user_id": "user1"}
        )
        assert result["result"] == "unregistered"

        TOOL_REGISTRY.pop("unregistered_tool", None)

    async def test_execute_tool_with_conversation_context(self):
        """Runtime context with conversation_id should be passed through."""
        handler = AsyncMock(return_value={"result": "success"})
        tool_def = ToolDefinition(
            name="context_tool",
            description="Takes context",
            parameters=[],
            handler=handler,
            category="testing",
        )
        TOOL_REGISTRY["context_tool"] = tool_def

        # Mock the permission store since imports are lazy inside the function
        with patch(
            "api.capabilities.permissions.CapabilityPermissionStore.check_permission",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await execute_tool_call(
                "context_tool",
                {},
                runtime_context={"user_id": "user1", "conversation_id": "conv1"},
            )
            assert handler.called

        TOOL_REGISTRY.pop("context_tool", None)
