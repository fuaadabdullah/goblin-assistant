"""
Integration tests for tool executor instrumentation with tracer
"""

import pytest

from api.observability.tool_tracer import ToolExecutionStatus, tool_tracer


@pytest.fixture
async def mock_conversation_context():
    """Create a mock conversation context"""
    return {
        "conversation_id": "conv-test-123",
        "user_id": "user-test-456",
        "request_id": "req-test-789",
    }


@pytest.fixture
async def mock_tool_result():
    """Create a mock tool execution result"""
    return {
        "summary": "Portfolio analysis complete",
        "performance": {"return": "8.5%"},
        "risks": ["concentration"],
    }


class TestExecutorTracing:
    """Test that executor properly instruments tool calls with tracer"""

    @pytest.mark.asyncio
    async def test_tool_execution_is_traced(self, mock_conversation_context):
        """Test that a single tool execution is properly traced"""
        # Setup
        request_id = mock_conversation_context["request_id"]
        conversation_id = mock_conversation_context["conversation_id"]
        user_id = mock_conversation_context["user_id"]

        # Start trace (simulating what run_tool_loop does)
        trace_id = tool_tracer.start_trace(
            request_id=request_id,
            conversation_id=conversation_id,
            user_id=user_id,
            tool_count=1,
        )

        assert trace_id is not None

        # Start round
        tool_tracer.start_round(trace_id, 0, ["portfolio_analyzer"])

        # Record execution (simulating what run_tool_loop does for each tool)
        tool_tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="portfolio_analyzer",
            args_count=2,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=145.5,
            result_keys=["summary", "performance", "risks"],
            memory_promoted=True,
        )

        # End round
        tool_tracer.end_round(trace_id, 0)

        # End trace
        tool_tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=150.0,
            final_message_tokens=450,
        )

        # Verify trace was recorded
        result = tool_tracer.get_tool_trace(request_id)
        assert result is not None
        assert result["trace"]["request_id"] == request_id
        assert result["summary"]["total_executions"] == 1
        assert result["summary"]["success_rate"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_multiple_tool_rounds_are_traced(self, mock_conversation_context):
        """Test that multiple rounds of tool calls are traced correctly"""
        request_id = mock_conversation_context["request_id"]
        conversation_id = mock_conversation_context["conversation_id"]
        user_id = mock_conversation_context["user_id"]

        trace_id = tool_tracer.start_trace(
            request_id=request_id,
            conversation_id=conversation_id,
            user_id=user_id,
            tool_count=3,
        )

        # Round 1: 2 tools
        tool_tracer.start_round(trace_id, 0, ["fetch_data", "analyze_data"])

        tool_tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="fetch_data",
            args_count=1,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=100.0,
            result_keys=["data"],
        )

        tool_tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="analyze_data",
            args_count=1,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=150.0,
            result_keys=["analysis"],
            memory_promoted=True,
        )

        tool_tracer.end_round(trace_id, 0)

        # Round 2: 1 tool
        tool_tracer.start_round(trace_id, 1, ["generate_report"])

        tool_tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=1,
            tool_name="generate_report",
            args_count=2,
            status=ToolExecutionStatus.SUCCESS.value,
            elapsed_ms=200.0,
            result_keys=["report", "pdf_url"],
            visualization_extracted=True,
        )

        tool_tracer.end_round(trace_id, 1)

        # End trace
        tool_tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=450.0,
            final_message_tokens=600,
        )

        # Verify
        result = tool_tracer.get_tool_trace(request_id)
        trace = result["trace"]

        assert len(trace["rounds"]) == 2
        assert len(trace["rounds"][0]["executions"]) == 2
        assert len(trace["rounds"][1]["executions"]) == 1

        assert result["summary"]["total_rounds"] == 2
        assert result["summary"]["total_executions"] == 3
        assert result["summary"]["memory_promoted_count"] == 1
        assert result["summary"]["visualizations_count"] == 1

    @pytest.mark.asyncio
    async def test_tool_failure_is_traced(self, mock_conversation_context):
        """Test that tool failures are properly traced"""
        request_id = mock_conversation_context["request_id"]
        conversation_id = mock_conversation_context["conversation_id"]
        user_id = mock_conversation_context["user_id"]

        trace_id = tool_tracer.start_trace(
            request_id=request_id,
            conversation_id=conversation_id,
            user_id=user_id,
            tool_count=1,
        )

        tool_tracer.start_round(trace_id, 0, ["risky_tool"])

        tool_tracer.record_tool_execution(
            trace_id=trace_id,
            round_number=0,
            tool_name="risky_tool",
            args_count=1,
            status=ToolExecutionStatus.FAILURE.value,
            elapsed_ms=50.0,
            error="Tool execution failed: Timeout after 30s",
        )

        tool_tracer.end_round(trace_id, 0, error="Tool failure")

        tool_tracer.end_trace(
            trace_id=trace_id,
            total_time_ms=50.0,
            final_message_tokens=100,
            error="Tool execution failed during round 0",
        )

        # Verify failure was recorded
        result = tool_tracer.get_tool_trace(request_id)

        assert result["trace"]["error"] == "Tool execution failed during round 0"
        assert result["summary"]["success_rate"] == pytest.approx(0.0)
        assert (
            result["trace"]["rounds"][0]["executions"][0]["error"]
            == "Tool execution failed: Timeout after 30s"
        )

    @pytest.mark.asyncio
    async def test_conversation_traces_indexed_correctly(self):
        """Test that traces are indexed by conversation_id"""
        conversation_id = "conv-integration-test"
        user_id = "user-integration-test"

        # Create 3 traces for the same conversation
        for i in range(3):
            request_id = f"req-integration-{i}"

            trace_id = tool_tracer.start_trace(
                request_id=request_id,
                conversation_id=conversation_id,
                user_id=user_id,
                tool_count=1,
            )

            tool_tracer.start_round(trace_id, 0, ["tool1"])
            tool_tracer.record_tool_execution(
                trace_id=trace_id,
                round_number=0,
                tool_name="tool1",
                args_count=1,
                status=ToolExecutionStatus.SUCCESS.value,
                elapsed_ms=100.0 + i * 10,
                result_keys=["result"],
            )
            tool_tracer.end_round(trace_id, 0)

            tool_tracer.end_trace(
                trace_id=trace_id,
                total_time_ms=100.0 + i * 10,
                final_message_tokens=100,
            )

        # Retrieve all traces for conversation
        result = tool_tracer.get_conversation_tool_traces(
            conversation_id=conversation_id, limit=10, offset=0
        )

        assert result["conversation_id"] == conversation_id
        assert result["total_count"] == 3
        assert len(result["traces"]) == 3

        # Verify traces are different
        request_ids = [t["trace"]["request_id"] for t in result["traces"]]
        assert len(set(request_ids)) == 3

    @pytest.mark.asyncio
    async def test_pagination_works_correctly(self):
        """Test that pagination of conversation traces works"""
        conversation_id = "conv-pagination-test"
        user_id = "user-pagination-test"

        # Create 15 traces
        for i in range(15):
            request_id = f"req-pagination-{i}"

            trace_id = tool_tracer.start_trace(
                request_id=request_id,
                conversation_id=conversation_id,
                user_id=user_id,
                tool_count=1,
            )

            tool_tracer.start_round(trace_id, 0, ["tool"])
            tool_tracer.record_tool_execution(
                trace_id=trace_id,
                round_number=0,
                tool_name="tool",
                args_count=1,
                status=ToolExecutionStatus.SUCCESS.value,
                elapsed_ms=50.0,
                result_keys=["r"],
            )
            tool_tracer.end_round(trace_id, 0)

            tool_tracer.end_trace(
                trace_id=trace_id,
                total_time_ms=50.0,
                final_message_tokens=50,
            )

        # Test first page
        page1 = tool_tracer.get_conversation_tool_traces(
            conversation_id=conversation_id, limit=5, offset=0
        )
        assert len(page1["traces"]) == 5
        assert page1["total_count"] == 15

        # Test second page
        page2 = tool_tracer.get_conversation_tool_traces(
            conversation_id=conversation_id, limit=5, offset=5
        )
        assert len(page2["traces"]) == 5

        # Test third page
        page3 = tool_tracer.get_conversation_tool_traces(
            conversation_id=conversation_id, limit=5, offset=10
        )
        assert len(page3["traces"]) == 5

        # Verify no overlap
        ids_p1 = {t["trace"]["request_id"] for t in page1["traces"]}
        ids_p2 = {t["trace"]["request_id"] for t in page2["traces"]}
        ids_p3 = {t["trace"]["request_id"] for t in page3["traces"]}

        assert len(ids_p1 & ids_p2) == 0
        assert len(ids_p2 & ids_p3) == 0
        assert len(ids_p1 & ids_p3) == 0


class TestTracerStatistics:
    """Test statistics aggregation"""

    @pytest.mark.asyncio
    async def test_statistics_aggregation(self):
        """Test that statistics are correctly aggregated"""
        user_id = "user-stats-test"

        # Create traces with varying success/failure rates
        for i in range(4):
            request_id = f"req-stats-{i}"
            conversation_id = f"conv-stats-{i}"

            trace_id = tool_tracer.start_trace(
                request_id=request_id,
                conversation_id=conversation_id,
                user_id=user_id,
                tool_count=2,
            )

            tool_tracer.start_round(trace_id, 0, ["tool1", "tool2"])

            # First tool always succeeds
            tool_tracer.record_tool_execution(
                trace_id=trace_id,
                round_number=0,
                tool_name="tool1",
                args_count=1,
                status=ToolExecutionStatus.SUCCESS.value,
                elapsed_ms=100.0,
                result_keys=["r1"],
            )

            # Second tool: varies success/failure
            status = (
                ToolExecutionStatus.SUCCESS.value if i < 3 else ToolExecutionStatus.FAILURE.value
            )
            tool_tracer.record_tool_execution(
                trace_id=trace_id,
                round_number=0,
                tool_name="tool2",
                args_count=1,
                status=status,
                elapsed_ms=150.0,
                result_keys=["r2"] if i < 3 else None,
            )

            tool_tracer.end_round(trace_id, 0)

            tool_tracer.end_trace(
                trace_id=trace_id,
                total_time_ms=250.0,
                final_message_tokens=200,
            )

        # Get statistics
        stats = tool_tracer.get_tool_trace_stats(user_id=user_id, time_window_hours=24)

        assert stats["trace_count"] == 4
        assert stats["stats"]["avg_executions_per_trace"] == pytest.approx(2.0)

        # 7 successes out of 8 = 87.5%
        assert stats["stats"]["avg_success_rate"] > 0.8
