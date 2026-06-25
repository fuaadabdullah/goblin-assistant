"""Capability models used by the assistant tool permission gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class CapabilityType(str, Enum):
    """Supported capability groupings."""

    TOOL = "tool"


@dataclass(slots=True)
class Capability:
    """Capability definition for a set of tools."""

    id: str
    type: CapabilityType
    name: str
    description: str
    tool_names: List[str] = field(default_factory=list)
    requires_explicit_grant: bool = False
