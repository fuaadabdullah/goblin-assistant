"""In-memory capability registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .models import Capability


@dataclass
class CapabilityRegistry:
    """Track capabilities and the tools they protect."""

    _capabilities: Dict[str, Capability] = field(default_factory=dict)
    _tool_to_cap: Dict[str, str] = field(default_factory=dict)

    def register(self, capability: Capability) -> Capability:
        self._capabilities[capability.id] = capability
        for tool_name in capability.tool_names:
            self._tool_to_cap[tool_name] = capability.id
        return capability

    def get(self, capability_id: str) -> Optional[Capability]:
        return self._capabilities.get(capability_id)

    def get_for_tool(self, tool_name: str) -> Optional[Capability]:
        capability_id = self._tool_to_cap.get(tool_name)
        if capability_id is None:
            return None
        return self._capabilities.get(capability_id)


capability_registry = CapabilityRegistry()
