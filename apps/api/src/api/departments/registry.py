"""Department registry — defines the provider chain for each department.

This is the single source of truth for which providers back which departments.
Edit this file to change department → provider assignments without touching
any other code. Provider IDs here match internal IDs in config/providers.toml.

The chain order matters: the first configured provider is tried first,
remaining entries are fallbacks tried in order on failure.
"""

from __future__ import annotations

from typing import Dict, List

from .models import DepartmentId, DepartmentPolicy, DepartmentQualityTier

# ── Department policy definitions ──────────────────────────────────────
# Each entry in provider_chain is (provider_id, model_name).
# provider_id must match a key in config/providers.toml.

_DEPARTMENT_POLICIES: Dict[DepartmentId, DepartmentPolicy] = {
    DepartmentId.REASONING: DepartmentPolicy(
        department_id=DepartmentId.REASONING,
        display_name="Reasoning",
        description="Logic, analysis, planning, math, and problem-solving",
        provider_chain=[
            ("openai", "gpt-4o"),
            ("anthropic", "claude-sonnet-4-20250514"),
            ("gemini", "gemini-2.5-flash-001"),
        ],
        default_tier=DepartmentQualityTier.BALANCED,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        max_tokens=8192,
        temperature_default=0.5,
    ),
    DepartmentId.CODING: DepartmentPolicy(
        department_id=DepartmentId.CODING,
        display_name="Coding",
        description="Code generation, debugging, refactoring, code review",
        provider_chain=[
            ("anthropic", "claude-sonnet-4-20250514"),
            ("openai", "gpt-4o"),
            ("gemini", "gemini-2.5-flash-001"),
        ],
        default_tier=DepartmentQualityTier.BALANCED,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        max_tokens=8192,
        temperature_default=0.3,
    ),
    DepartmentId.CREATIVE: DepartmentPolicy(
        department_id=DepartmentId.CREATIVE,
        display_name="Creative",
        description="Writing, brainstorming, content creation",
        provider_chain=[
            ("openai", "gpt-4o"),
            ("anthropic", "claude-sonnet-4-20250514"),
            ("gemini", "gemini-2.5-flash-001"),
        ],
        default_tier=DepartmentQualityTier.BALANCED,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        max_tokens=4096,
        temperature_default=0.8,
    ),
    DepartmentId.RECALL: DepartmentPolicy(
        department_id=DepartmentId.RECALL,
        display_name="Recall",
        description="Memory retrieval, context assembly, information lookup",
        provider_chain=[
            ("openai", "gpt-4o-mini"),
            ("gemini", "gemini-2.5-flash-001"),
            ("anthropic", "claude-sonnet-4-20250514"),
        ],
        default_tier=DepartmentQualityTier.SPEED,
        supports_streaming=True,
        supports_tools=False,
        supports_vision=False,
        max_tokens=2048,
        temperature_default=0.3,
    ),
    DepartmentId.TOOL_USE: DepartmentPolicy(
        department_id=DepartmentId.TOOL_USE,
        display_name="Tools",
        description="Function calling, structured actions, automation",
        provider_chain=[
            ("openai", "gpt-4o"),
            ("anthropic", "claude-sonnet-4-20250514"),
            ("gemini", "gemini-2.5-flash-001"),
        ],
        default_tier=DepartmentQualityTier.BALANCED,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        max_tokens=4096,
        temperature_default=0.3,
    ),
    DepartmentId.RESEARCH: DepartmentPolicy(
        department_id=DepartmentId.RESEARCH,
        display_name="Research",
        description="Deep research, multi-source synthesis, investigation",
        provider_chain=[
            ("gemini", "gemini-2.5-flash-001"),
            ("openai", "gpt-4o"),
            ("anthropic", "claude-sonnet-4-20250514"),
        ],
        default_tier=DepartmentQualityTier.QUALITY,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        max_tokens=8192,
        temperature_default=0.5,
    ),
    DepartmentId.GENERAL: DepartmentPolicy(
        department_id=DepartmentId.GENERAL,
        display_name="General",
        description="General-purpose assistant for uncategorized requests",
        provider_chain=[
            ("openai", "gpt-4o-mini"),
            ("gemini", "gemini-2.5-flash-001"),
            ("anthropic", "claude-sonnet-4-20250514"),
        ],
        default_tier=DepartmentQualityTier.SPEED,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        max_tokens=4096,
        temperature_default=0.7,
    ),
}


class DepartmentRegistry:
    """Registry of all department policies.

    Provides lookup by department_id and iteration over all departments.
    """

    def __init__(self, policies: Dict[DepartmentId, DepartmentPolicy]) -> None:
        self._policies: Dict[DepartmentId, DepartmentPolicy] = dict(policies)

    def get(self, dept_id: DepartmentId) -> DepartmentPolicy:
        """Get the policy for a department. Raises KeyError if not found."""
        return self._policies[dept_id]

    def get_by_id_str(self, dept_id_str: str) -> DepartmentPolicy:
        """Lookup by string value (e.g. 'reasoning'). Raises KeyError if not found."""
        dept_id = DepartmentId(dept_id_str.strip().lower())
        return self._policies[dept_id]

    def list_ids(self) -> List[str]:
        """Return all department IDs as strings (public-facing)."""
        return [d.value for d in self._policies]

    def list_policies(self) -> List[DepartmentPolicy]:
        """Return all policies."""
        return list(self._policies.values())

    def list_public(self) -> List[Dict[str, str]]:
        """Return public-facing department summaries — NO provider details."""
        result: List[Dict[str, str]] = []
        for policy in self._policies.values():
            result.append(
                {
                    "department": policy.department_id.value,
                    "name": policy.display_name,
                    "description": policy.description,
                    "supports_streaming": str(policy.supports_streaming),
                    "supports_tools": str(policy.supports_tools),
                }
            )
        return result

    def provider_supports_tools(self, resolved_provider: str) -> bool:
        """Check if any department policy uses this provider with tools.

        Used to determine whether to include tool schemas in a call.
        """
        for policy in self._policies.values():
            for pid, _model in policy.provider_chain:
                if pid == resolved_provider and policy.supports_tools:
                    return True
        return False


# Singleton — constructed once at import time
DEPARTMENT_REGISTRY: DepartmentRegistry = DepartmentRegistry(_DEPARTMENT_POLICIES)
