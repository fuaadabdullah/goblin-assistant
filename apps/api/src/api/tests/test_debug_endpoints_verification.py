"""
Verification test for debug endpoints
"""

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.observability.tool_tracer import tool_tracer, ToolExecutionStatus
from api.observability.debug_router import router


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


def test_tool_trace_debug_endpoint():
    """Test GET /debug/tool-trace/{request_id} endpoint"""
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

    # Query the endpoint
    response = client.get(f"/debug/tool-trace/{request_id}")

    # With ops access decorator, should be 401 Unauthorized (auth required)
    # or 403 Forbidden (no permission)
    # or 200 OK (if auth is mocked/disabled in tests)
    assert response.status_code in [200, 401, 403], (
        f"Unexpected status code: {response.status_code}"
    )

    # If auth is disabled in tests, verify response structure
    if response.status_code == 200:
        data = response.json()
        assert "trace" in data
        assert "summary" in data
        assert data["trace"]["request_id"] == request_id


def test_conversation_traces_debug_endpoint():
    """Test GET /debug/tool-trace/conversation/{conversation_id} endpoint"""
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

    # Query the endpoint
    response = client.get(
        f"/debug/tool-trace/conversation/{conversation_id}"
    )

    assert response.status_code in [200, 401, 403]

    if response.status_code == 200:
        data = response.json()
        assert "conversation_id" in data
        assert "traces" in data
        assert data["conversation_id"] == conversation_id


def test_stats_debug_endpoint():
    """Test GET /debug/tool-trace/stats endpoint"""
    response = client.get("/debug/tool-trace/stats")

    # Expect 401 (auth required), 403 (no permission), or 200 (success)
    assert response.status_code in [200, 401, 403]

    if response.status_code == 200:
        data = response.json()
        assert "trace_count" in data
        assert "stats" in data
