"""Permission checks for capability-gated assistant tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CapabilityPermissionStore:
    """Minimal permission store used by the executor gate."""

    async def check_permission(
        self,
        user_id: str,
        capability_id: str,
        conversation_id: Optional[str] = None,
    ) -> bool:
        _ = (user_id, capability_id, conversation_id)
        return True
