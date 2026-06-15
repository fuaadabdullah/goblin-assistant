"""
Verification test for debug endpoints
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.observability.debug_router import get_memory_debug_info, router
from api.observability.tool_tracer import ToolExecutionStatus, tool_tracer

app = FastAPI()
app.include_router(router)


client = TestClient(app)


def test_debug_endpoints_are_registered():
    """Verify debug endpoints are registered"""
    routes = [route.path for route in app.routes]

    # Check that tool trace endpoints exist
    assert any("/debug/tool-trace/" in r for r in routes), (
        "Tool trace endpoints not registered in debug router"
    )


def test_tool_trace_debug_endpoint_requires_auth():
    """Test GET /debug/tool-trace/{request_id} returns 401 without valid ops credentials."""
    # Create a trace
    request_id = "test-req-verify-001"
    conversation_id = "test-conv-verify"
    user_id = "test-user-verify"

    trace_id = tool_tracer.start_trace(
        request_id=request_id,
        conversation_id=conversation_id,
        user_id=user_id,
        tool_count=1,
    )

    tool_tracer.start_round(trace_id, 0, ["test_tool"])
    tool_tracer.record_tool_execution(
        trace_id=trace_id,
        round_number=0,
        tool_name="test_tool",
        args_count=1,
        status=ToolExecutionStatus.SUCCESS.value,
        elapsed_ms=100.0,
        result_keys=["output"],
    )
    tool_tracer.end_round(trace_id, 0)
    tool_tracer.end_trace(
        trace_id=trace_id,
        total_time_ms=100.0,
        final_message_tokens=100,
    )

    # Query the endpoint without credentials
    response = client.get(f"/debug/tool-trace/{request_id}")

    # Without credentials, the ops access decorator returns 401 Unauthorized
    assert response.status_code == 401, (
        f"Expected 401 Unauthorized without credentials, got {response.status_code}: {response.json()}"
    )
    body = response.json()
    assert "detail" in body
    assert "Authentication required" in body["detail"] or "required" in body["detail"].lower()


def test_conversation_traces_debug_endpoint_requires_auth():
    """Test GET /debug/tool-trace/conversation/{conversation_id} returns 401 without credentials."""
    conversation_id = "test-conv-endpoint"

    # Create a trace
    request_id = "test-req-endpoint-001"

    trace_id = tool_tracer.start_trace(
        request_id=request_id,
        conversation_id=conversation_id,
        user_id="test-user",
        tool_count=1,
    )

    tool_tracer.start_round(trace_id, 0, ["test_tool"])
    tool_tracer.record_tool_execution(
        trace_id=trace_id,
        round_number=0,
        tool_name="test_tool",
        args_count=1,
        status=ToolExecutionStatus.SUCCESS.value,
        elapsed_ms=100.0,
        result_keys=["output"],
    )
    tool_tracer.end_round(trace_id, 0)
    tool_tracer.end_trace(
        trace_id=trace_id,
        total_time_ms=100.0,
        final_message_tokens=100,
    )

    # Query the endpoint without credentials
    response = client.get(f"/debug/tool-trace/conversation/{conversation_id}")

    # Without credentials, the ops access decorator returns 401 Unauthorized
    assert response.status_code == 401, (
        f"Expected 401 Unauthorized without credentials, got {response.status_code}: {response.json()}"
    )
    body = response.json()
    assert "detail" in body


def test_stats_debug_endpoint_requires_auth():
    """Test GET /debug/tool-trace/stats returns 401 without credentials."""
    response = client.get("/debug/tool-trace/stats")

    # Without credentials, the ops access decorator returns 401 Unauthorized
    assert response.status_code == 401, (
        f"Expected 401 Unauthorized without credentials, got {response.status_code}: {response.json()}"
    )
    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_memory_debug_info_includes_canonical_memory_items(monkeypatch):
    async def fake_get_user_memory(user_id: str):
        return {
            "memory_items": [
                {
                    "id": "mem-1",
                    "type": "preference",
                    "scope": "global",
                    "content": "User prefers concise answers.",
                    "summary": "Prefers concise answers",
                    "source": "conversation",
                    "source_ref": {"conversation_id": "conv-1"},
                    "confidence": 0.93,
                    "importance": 0.82,
                    "recency_score": 0.71,
                    "sensitivity": "low",
                    "status": "active",
                    "tags": ["preference"],
                    "entities": ["user"],
                    "embedding_id": "emb-1",
                }
            ],
            "promotion_history": [],
        }

    async def fake_get_memory_health(user_id: str):
        return {"user_id": user_id, "status": "ok"}

    monkeypatch.setattr(
        "api.observability.debug_write_router.get_user_memory",
        fake_get_user_memory,
    )
    monkeypatch.setattr(
        "api.observability.debug_write_router.get_memory_health",
        fake_get_memory_health,
    )

    result = await get_memory_debug_info("user-123")

    assert result["memory_items"][0]["type"] == "preference"
    assert result["memory_items"][0]["source_ref"] == {"conversation_id": "conv-1"}
    assert result["promotion_history"] == []
