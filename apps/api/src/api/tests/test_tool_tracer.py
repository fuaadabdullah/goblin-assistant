"""
Unit tests for the Tool Tracer service
"""

import pytest
from datetime import datetime, timezone

from api.observability.tool_tracer import (
    ToolTracer,
    ToolTrace,
    RoundData,
    ToolExecution,
    ToolExecutionStatus,
    RetryInfo,
)


@pytest.fixture
def tracer():
    """Create a fresh ToolTracer instance for each test"""
    return ToolTracer()


class TestToolTracerBasics:
    """Test basic ToolTracer functionality"""

    def test_start_trace_returns_trace_id(self, tracer):
        """Test that start_trace returns a valid trace_id"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=3,
        )

        assert trace_id is not None
        assert isinstance(trace_id, str)
        assert len(trace_id) > 0

    def test_start_trace_creates_active_trace(self, tracer):
        """Test that start_trace creates an active trace"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=3,
        )

        assert trace_id in tracer._active_traces
        trace = tracer._active_traces[trace_id]
        assert trace.request_id == "req-123"
        assert trace.conversation_id == "conv-456"
        assert trace.user_id == "user-789"

    def test_start_round_adds_round_to_trace(self, tracer):
        """Test that start_round adds a round to the trace"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=2,
        )

        tracer.start_round(trace_id, 0, ["tool1", "tool2"])

        trace = tracer._active_traces[trace_id]
        assert len(trace.rounds) == 1
        assert trace.rounds[0].round_number == 0
        assert trace.rounds[0].tools_called == ["tool1", "tool2"]

    def test_record_tool_execution(self, tracer):
        """Test recording a single tool execution"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=1,
        )

        tracer.start_round(trace_id, 0, ["portfolio_analyzer"])

        tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="portfolio_analyzer",
            args_count=2,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=150.5,
            result_keys=["summary", "performance", "risks"],
            memory_promoted=True,
            visualization_extracted=True,
        )

        trace = tracer._active_traces[trace_id]
        execution = trace.rounds[0].executions[0]

        assert execution.tool_name == "portfolio_analyzer"
        assert execution.status == ToolExecutionStatus.SUCCESS.value
        assert execution.elapsed_ms == 150.5
        assert execution.result_keys == ["summary", "performance", "risks"]
        assert execution.memory_promoted is True
        assert execution.visualization_extracted is True

    def test_end_trace_moves_to_cache(self, tracer):
        """Test that end_trace moves trace from active to cache"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=0,
        )

        assert trace_id in tracer._active_traces
        assert "req-123" not in tracer._trace_cache

        tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=200.0,
            final_message_tokens=500,
            error=None,
        )

        assert trace_id not in tracer._active_traces
        assert "req-123" in tracer._trace_cache

    def test_get_tool_trace_retrieves_trace(self, tracer):
        """Test retrieving a tool trace by request_id"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=1,
        )

        tracer.start_round(trace_id, 0, ["tool1"])
        tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="tool1",
            args_count=1,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=100.0,
            result_keys=["result"],
        )
        tracer.end_round(trace_id, 0)

        tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=100.0,
            final_message_tokens=100,
        )

        result = tracer.get_tool_trace("req-123")

        assert result is not None
        assert "trace" in result
        assert "summary" in result
        assert result["summary"]["total_rounds"] == 1
        assert result["summary"]["total_executions"] == 1
        assert result["summary"]["success_rate"] == 1.0


class TestToolTraceMultipleRounds:
    """Test tracing with multiple rounds"""

    def test_multiple_rounds_execution(self, tracer):
        """Test tracing through multiple tool-calling rounds"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=3,
        )

        # Round 1: Execute 2 tools
        tracer.start_round(trace_id, 0, ["tool1", "tool2"])
        tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="tool1",
            args_count=1,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=100.0,
            result_keys=["output"],
        )
        tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="tool2",
            args_count=1,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=150.0,
            result_keys=["output"],
        )
        tracer.end_round(trace_id, 0)

        # Round 2: Execute 1 tool
        tracer.start_round(trace_id, 1, ["tool3"])
        tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=1,
            tool_name="tool3",
            args_count=1,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=200.0,
            result_keys=["final_result"],
        )
        tracer.end_round(trace_id, 1)

        tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=450.0,
            final_message_tokens=300,
        )

        trace = tracer._trace_cache["req-123"]
        assert len(trace.rounds) == 2
        assert len(trace.rounds[0].executions) == 2
        assert len(trace.rounds[1].executions) == 1

        summary = trace.get_summary()
        assert summary["total_rounds"] == 2
        assert summary["total_executions"] == 3
        assert summary["success_rate"] == 1.0


class TestToolTraceErrorHandling:
    """Test error handling in tool tracing"""

    def test_record_execution_with_error(self, tracer):
        """Test recording a failed tool execution"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=1,
        )

        tracer.start_round(trace_id, 0, ["tool1"])
        tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="tool1",
            args_count=1,
            status=ToolExecutionStatus.FAILURE.value,
            elapsed_ms=50.0,
            result_keys=None,
            error="Tool execution timed out",
        )
        tracer.end_round(trace_id, 0, error="Tool failure")

        tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=50.0,
            final_message_tokens=100,
            error="Tool execution failed",
        )

        trace = tracer._trace_cache["req-123"]
        assert trace.error == "Tool execution failed"
        assert trace.rounds[0].error == "Tool failure"
        assert trace.rounds[0].executions[0].error == "Tool execution timed out"

        summary = trace.get_summary()
        assert summary["success_rate"] == 0.0


class TestToolTraceStatistics:
    """Test statistics gathering"""

    def test_get_conversation_tool_traces(self, tracer):
        """Test retrieving all traces for a conversation"""
        conv_id = "conv-456"

        # Create 3 traces for the same conversation
        for i in range(3):
            trace_id = tracer.start_trace(
                request_id=f"req-{i}",
                conversation_id=conv_id,
                user_id="user-789",
                tool_count=1,
            )

            tracer.start_round(trace_id, 0, ["tool1"])
            tracer.record_tool_execution(
                trace_id=trace_id,
                round_number=0,
                tool_name="tool1",
                args_count=1,
                status=ToolExecutionStatus.SUCCESS.value,
                elapsed_ms=100.0 + i * 50,
                result_keys=["output"],
            )
            tracer.end_round(trace_id, 0)

            tracer.end_trace(
                trace_id=trace_id,
                total_time_ms=100.0 + i * 50,
                final_message_tokens=100,
            )

        result = tracer.get_conversation_tool_traces(
            conversation_id=conv_id, limit=10, offset=0
        )

        assert result["conversation_id"] == conv_id
        assert result["total_count"] == 3
        assert len(result["traces"]) == 3

    def test_get_tool_trace_stats(self, tracer):
        """Test aggregated statistics for tool traces"""
        user_id = "user-789"

        # Create 5 traces
        for i in range(5):
            trace_id = tracer.start_trace(
                request_id=f"req-{i}",
                conversation_id=f"conv-{i}",
                user_id=user_id,
                tool_count=2,
            )

            tracer.start_round(trace_id, 0, ["tool1", "tool2"])
            tracer.record_tool_execution(
                trace_id=trace_id,
                round_number=0,
                tool_name="tool1",
                args_count=1,
                status=ToolExecutionStatus.SUCCESS.value,
                elapsed_ms=100.0,
                result_keys=["output"],
            )
            tracer.record_tool_execution(
                trace_id=trace_id,
                round_number=0,
                tool_name="tool2",
                args_count=1,
                status=ToolExecutionStatus.SUCCESS.value,
                elapsed_ms=150.0,
                result_keys=["output"],
            )
            tracer.end_round(trace_id, 0)

            tracer.end_trace(
                trace_id=trace_id,
                total_time_ms=250.0,
                final_message_tokens=100,
            )

        stats = tracer.get_tool_trace_stats(
            user_id=user_id, time_window_hours=24
        )

        assert stats["trace_count"] == 5
        assert stats["stats"]["avg_executions_per_trace"] == 2.0
        assert stats["stats"]["avg_success_rate"] == 1.0


class TestToolTraceSerialization:
    """Test serialization of tool traces"""

    def test_trace_to_dict(self, tracer):
        """Test converting trace to dictionary"""
        trace_id = tracer.start_trace(
            request_id="req-123",
            conversation_id="conv-456",
            user_id="user-789",
            tool_count=1,
        )

        tracer.start_round(trace_id, 0, ["tool1"])
        tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="tool1",
            args_count=1,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=100.0,
            result_keys=["output"],
        )
        tracer.end_round(trace_id, 0)

        tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=100.0,
            final_message_tokens=100,
        )

        trace = tracer._trace_cache["req-123"]
        trace_dict = trace.to_dict()

        assert trace_dict["request_id"] == "req-123"
        assert trace_dict["conversation_id"] == "conv-456"
        assert trace_dict["user_id"] == "user-789"
        assert len(trace_dict["rounds"]) == 1
        assert isinstance(trace_dict["timestamp"], str)
