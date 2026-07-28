"""Provider-neutral contracts for assistant tool orchestration.

assistant_tools is the canonical tool system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class StreamEventType(str, Enum):
    TOKEN = "TOKEN"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    STATUS = "STATUS"
    ERROR = "ERROR"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    tool_name: str
    payload: Dict[str, Any]


__all__ = ["StreamEventType", "ToolCall", "ToolResult"]
