"""
Tool Execution Trace System
Comprehensive tracing for every step of tool execution with full observability
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from enum import Enum
import structlog
import uuid

logger = structlog.get_logger()


class ToolExecutionStatus(Enum):
    """Status of a single tool execution"""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class RetryInfo:
    """Information about tool retry attempts"""

    attempt: int
    max_retries: int
    backoff_seconds: float
    transient_error: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ToolExecution:
    """Single tool execution within a round"""

    tool_name: str
    status: str  # ToolExecutionStatus value
    elapsed_ms: float
    args_count: int
    result_keys: Optional[List[str]]
    error: Optional[str]
    retry_info: Optional[RetryInfo] = None
    memory_promoted: bool = False
    visualization_extracted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        data = asdict(self)
        if self.retry_info:
            data["retry_info"] = self.retry_info.to_dict()
        return data


@dataclass
class RoundData:
    """Single round of tool calling"""

    round_number: int
    tools_called: List[str]
    executions: List[ToolExecution]
    round_time_ms: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "round_number": self.round_number,
            "tools_called": self.tools_called,
            "executions": [e.to_dict() for e in self.executions],
            "round_time_ms": self.round_time_ms,
            "error": self.error,
        }


@dataclass
class ToolTrace:
    """Complete tool execution trace for a request"""

    request_id: str
    trace_id: str
    conversation_id: Optional[str]
    user_id: Optional[str]
    timestamp: datetime
    rounds: List[RoundData] = field(default_factory=list)
    total_time_ms: float = 0.0
    final_message_tokens: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "rounds": [r.to_dict() for r in self.rounds],
            "total_time_ms": self.total_time_ms,
            "final_message_tokens": self.final_message_tokens,
            "error": self.error,
        }

    def to_json(self) -> str:
        """Convert to JSON string for structured logging"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the trace"""
        all_executions = []
        for round_data in self.rounds:
            all_executions.extend(round_data.executions)

        success_count = sum(
            1 for e in all_executions if e.status == ToolExecutionStatus.SUCCESS.value
        )
        failure_count = sum(
            1 for e in all_executions if e.status == ToolExecutionStatus.FAILURE.value
        )
        total_exec_time_ms = sum(e.elapsed_ms for e in all_executions)
        avg_exec_time_ms = total_exec_time_ms / len(all_executions) if all_executions else 0
        promoted_count = sum(1 for e in all_executions if e.memory_promoted)
        visualizations_count = sum(1 for e in all_executions if e.visualization_extracted)

        # Find slowest tool
        slowest_tool = None
        max_time = 0
        for e in all_executions:
            if e.elapsed_ms > max_time:
                max_time = e.elapsed_ms
                slowest_tool = e.tool_name

        return {
            "total_rounds": len(self.rounds),
            "total_executions": len(all_executions),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": (
                round(success_count / len(all_executions), 3) if all_executions else 1.0
            ),
            "total_exec_time_ms": round(total_exec_time_ms, 2),
            "avg_exec_time_ms": round(avg_exec_time_ms, 2),
            "memory_promoted_count": promoted_count,
            "visualizations_count": visualizations_count,
            "slowest_tool": slowest_tool,
            "slowest_tool_time_ms": max_time,
        }


class ToolTracer:
    """Centralized tool execution tracing with full observability"""

    def __init__(self):
        self._trace_cache: Dict[str, ToolTrace] = {}  # Cache recent
        self._active_traces: Dict[str, ToolTrace] = {}  # Track in-flight
        self._trace_count = 0

    def start_trace(
        self,
        request_id: str,
        conversation_id: Optional[str],
        user_id: Optional[str],
        tool_count: int,
    ) -> str:
        """Start a new tool execution trace.

        Args:
            request_id: HTTP request ID for correlation
            conversation_id: Current conversation ID
            user_id: User ID for this trace
            tool_count: Number of tools available

        Returns:
            trace_id for use in subsequent calls
        """
        trace_id = str(uuid.uuid4())

        trace = ToolTrace(
            request_id=request_id,
            trace_id=trace_id,
            conversation_id=conversation_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
        )

        self._active_traces[trace_id] = trace
        self._trace_count += 1

        logger.info(
            "tool_trace_start",
            trace_id=trace_id,
            request_id=request_id,
            conversation_id=conversation_id,
            tool_count=tool_count,
        )

        return trace_id

    def start_round(self, trace_id: str, round_number: int, tools_to_call: List[str]) -> None:
        """Record the start of a tool execution round.

        Args:
            trace_id: Trace ID from start_trace()
            round_number: 0-indexed round number
            tools_to_call: List of tool names to execute this round
        """
        trace = self._active_traces.get(trace_id)
        if not trace:
            logger.warning("tool_round_start_unknown_trace", trace_id=trace_id)
            return

        # Create new round (will be populated with executions)
        round_data = RoundData(
            round_number=round_number,
            tools_called=tools_to_call,
            executions=[],
            round_time_ms=0.0,
        )
        trace.rounds.append(round_data)

        logger.info(
            "tool_round_start",
            trace_id=trace_id,
            round_number=round_number,
            tool_count=len(tools_to_call),
        )

    def record_tool_execution(
        self,
        trace_id: str,
        round_number: int,
        tool_name: str,
        args_count: int,
        status: str,
        elapsed_ms: float,
        result_keys: Optional[List[str]] = None,
        error: Optional[str] = None,
        retry_info: Optional[RetryInfo] = None,
        memory_promoted: bool = False,
        visualization_extracted: bool = False,
    ) -> None:
        """Record a single tool execution.

        Args:
            trace_id: Trace ID from start_trace()
            round_number: 0-indexed round number
            tool_name: Name of the tool executed
            args_count: Number of arguments passed
            status: Execution status (success, failure, timeout, skipped)
            elapsed_ms: Execution time in milliseconds
            result_keys: Keys in the result dict (if successful)
            error: Error message if failed
            retry_info: Retry information if applicable
            memory_promoted: Whether results were promoted to memory
            visualization_extracted: Whether visualizations were extracted
        """
        trace = self._active_traces.get(trace_id)
        if not trace:
            logger.warning(
                "tool_execution_record_unknown_trace",
                trace_id=trace_id,
                tool_name=tool_name,
            )
            return

        if not trace.rounds:
            logger.warning(
                "tool_execution_record_no_rounds",
                trace_id=trace_id,
                round_number=round_number,
            )
            return

        # Get current round (should be the last one)
        current_round = trace.rounds[-1]

        execution = ToolExecution(
            tool_name=tool_name,
            status=status,
            elapsed_ms=elapsed_ms,
            args_count=args_count,
            result_keys=result_keys,
            error=error,
            retry_info=retry_info,
            memory_promoted=memory_promoted,
            visualization_extracted=visualization_extracted,
        )

        current_round.executions.append(execution)

        # Log execution
        is_failure = status == ToolExecutionStatus.FAILURE.value
        log_fn = logger.error if is_failure else logger.info
        log_fn(
            "tool_execution_record",
            trace_id=trace_id,
            round_number=round_number,
            tool_name=tool_name,
            status=status,
            elapsed_ms=elapsed_ms,
            error=error,
            memory_promoted=memory_promoted,
        )

    def end_round(
        self,
        trace_id: str,
        round_number: int,
        error: Optional[str] = None,
    ) -> None:
        """Record the end of a tool execution round.

        Args:
            trace_id: Trace ID from start_trace()
            round_number: 0-indexed round number
            error: Any error that occurred during the round
        """
        trace = self._active_traces.get(trace_id)
        if not trace:
            return

        if trace.rounds and trace.rounds[-1].round_number == round_number:
            current_round = trace.rounds[-1]
            current_round.error = error

            # Calculate round time from executions
            round_time_ms = sum(e.elapsed_ms for e in current_round.executions)
            current_round.round_time_ms = round_time_ms

            logger.info(
                "tool_round_end",
                trace_id=trace_id,
                round_number=round_number,
                execution_count=len(current_round.executions),
                round_time_ms=round_time_ms,
            )

    def end_trace(
        self,
        trace_id: str,
        total_time_ms: float,
        final_message_tokens: int,
        error: Optional[str] = None,
    ) -> None:
        """Record the end of tool execution trace.

        Args:
            trace_id: Trace ID from start_trace()
            total_time_ms: Total time in milliseconds
            final_message_tokens: Token count of final message
            error: Any error that occurred during tool execution
        """
        trace = self._active_traces.get(trace_id)
        if not trace:
            return

        trace.total_time_ms = total_time_ms
        trace.final_message_tokens = final_message_tokens
        trace.error = error

        # Move from active to cache
        self._trace_cache[trace.request_id] = trace
        del self._active_traces[trace_id]

        # Log summary
        summary = trace.get_summary()
        logger.info(
            "tool_trace_end",
            trace_id=trace_id,
            request_id=trace.request_id,
            total_rounds=summary["total_rounds"],
            total_executions=summary["total_executions"],
            success_rate=summary["success_rate"],
            total_time_ms=total_time_ms,
            error=error,
        )

    def get_tool_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool trace by request ID.

        Args:
            request_id: HTTP request ID

        Returns:
            Complete trace data or None if not found
        """
        if request_id in self._trace_cache:
            trace = self._trace_cache[request_id]
            return {
                "trace": trace.to_dict(),
                "summary": trace.get_summary(),
            }
        return None

    def get_conversation_tool_traces(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get all tool traces for a conversation.

        Args:
            conversation_id: Conversation ID to filter by
            limit: Maximum number of traces to return
            offset: Pagination offset

        Returns:
            Paginated list of traces with pagination info
        """
        matching_traces = [
            trace
            for trace in self._trace_cache.values()
            if trace.conversation_id == conversation_id
        ]

        # Sort by timestamp descending
        matching_traces.sort(key=lambda x: x.timestamp, reverse=True)

        total_count = len(matching_traces)
        paginated_traces = matching_traces[offset : offset + limit]

        return {
            "conversation_id": conversation_id,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "traces": [
                {
                    "trace": trace.to_dict(),
                    "summary": trace.get_summary(),
                }
                for trace in paginated_traces
            ],
        }

    def get_tool_trace_stats(
        self,
        user_id: Optional[str] = None,
        time_window_hours: int = 24,
    ) -> Dict[str, Any]:
        """Get aggregate tool trace statistics.

        Args:
            user_id: Filter by user ID (optional)
            time_window_hours: Look back window

        Returns:
            Aggregate statistics
        """
        from datetime import timedelta

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

        # Filter traces
        traces = [
            trace
            for trace in self._trace_cache.values()
            if trace.timestamp >= cutoff_time and (not user_id or trace.user_id == user_id)
        ]

        if not traces:
            return {
                "user_id": user_id,
                "time_window_hours": time_window_hours,
                "trace_count": 0,
                "stats": None,
            }

        # Aggregate statistics
        all_summaries = [trace.get_summary() for trace in traces]

        trace_count = len(all_summaries)
        avg_rounds = sum(s["total_rounds"] for s in all_summaries) / trace_count
        avg_executions = sum(s["total_executions"] for s in all_summaries) / trace_count
        avg_success_rate = sum(s["success_rate"] for s in all_summaries) / trace_count
        avg_exec_time = sum(s["avg_exec_time_ms"] for s in all_summaries) / trace_count

        # Find slowest tools
        tool_times: Dict[str, List[float]] = {}
        for summary in all_summaries:
            if summary["slowest_tool"]:
                tool_name = summary["slowest_tool"]
                if tool_name not in tool_times:
                    tool_times[tool_name] = []
                tool_times[tool_name].append(summary["slowest_tool_time_ms"])

        slowest_tools = sorted(
            [
                {
                    "tool_name": name,
                    "avg_time_ms": sum(times) / len(times),
                    "call_count": len(times),
                }
                for name, times in tool_times.items()
            ],
            key=lambda x: x["avg_time_ms"],
            reverse=True,
        )[:5]

        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "trace_count": len(traces),
            "stats": {
                "avg_rounds": round(avg_rounds, 2),
                "avg_executions_per_trace": round(avg_executions, 2),
                "avg_success_rate": round(avg_success_rate, 3),
                "avg_execution_time_ms": round(avg_exec_time, 2),
                "total_promoted_count": sum(s["memory_promoted_count"] for s in all_summaries),
                "total_visualizations_count": sum(s["visualizations_count"] for s in all_summaries),
                "slowest_tools": slowest_tools,
            },
        }


# Global tool tracer instance
tool_tracer = ToolTracer()
