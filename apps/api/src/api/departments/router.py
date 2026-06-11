"""Department router — classifies messages into brain departments.

This is the decision layer that determines *which part of the brain*
should handle a request, without exposing *which provider* will do it.

The router uses the existing intent classification result and maps it
to a department via the INTENT_TO_DEPARTMENT table in models.py.
"""

from __future__ import annotations

from typing import Any, Optional

import structlog

from .models import (
    INTENT_TO_DEPARTMENT,
    DepartmentId,
    DepartmentQualityTier,
    DepartmentSelection,
    quality_tier_for_complexity,
)
from .registry import DEPARTMENT_REGISTRY

logger = structlog.get_logger()


class DepartmentRouter:
    """Classifies a message into a brain department.

    Uses the existing intent classification + complexity scoring pipeline.
    Pure stateless logic — safe to use as a singleton or per-request.
    """

    def classify(
        self,
        intent: Optional[Any] = None,
        task_type: Optional[str] = None,
        complexity_score: float = 0.0,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> DepartmentSelection:
        """Determine the best department for a request.

        Args:
            intent: IntentResult from the intent classifier (has .label and .confidence).
            task_type: Optional explicit task type string.
            complexity_score: 0.0–1.0 complexity from feature extractor.
            preferred_provider: Internal provider override (for migration compat).
            preferred_model: Internal model override (for migration compat).
            mode: Explicit mode string (e.g. "DEEP_RESEARCH", "GENERAL_ASSISTANT").

        Returns:
            DepartmentSelection with the chosen department, reason, and
            resolved provider (internal) ready for dispatch.
        """
        # ── Step 1: Determine department from intent label ────────────
        dept_id = self._department_from_intent(intent, task_type, mode)
        reason_parts: list[str] = []

        # ── Step 2: Determine quality tier from complexity ────────────
        tier = quality_tier_for_complexity(complexity_score)
        if dept_id == DepartmentId.RECALL:
            tier = DepartmentQualityTier.SPEED
        if dept_id == DepartmentId.RESEARCH:
            tier = DepartmentQualityTier.QUALITY

        # ── Step 3: Resolve provider from department policy ───────────
        policy = DEPARTMENT_REGISTRY.get(dept_id)
        resolved_provider, resolved_model = policy.primary_provider

        # If an explicit provider was given (transitional compat), use it
        if preferred_provider:
            resolved_provider = preferred_provider
            resolved_model = preferred_model or resolved_model
            reason_parts.append("explicit selection")

        # Build fallback chain (from the policy, excluding the primary)
        fallback_chain = [pid for pid, _model in policy.fallback_providers]

        reason_parts.append(f"handled by {dept_id.value}")
        if tier != DepartmentQualityTier.BALANCED:
            reason_parts.append(tier.value)

        reason = ", ".join(reason_parts)

        return DepartmentSelection(
            department_id=dept_id,
            reason=reason,
            resolved_provider=resolved_provider,
            resolved_model=resolved_model,
            quality_tier=tier,
            fallback_chain=fallback_chain,
        )

    def _department_from_intent(
        self,
        intent: Optional[Any],
        task_type: Optional[str],
        mode: Optional[str],
    ) -> DepartmentId:
        """Map intent/type/mode to a DepartmentId."""
        # Mode-based overrides
        if mode:
            mode_upper = str(mode).strip().upper()
            if mode_upper in ("RESEARCH", "DEEP_RESEARCH"):
                return DepartmentId.RESEARCH
            if mode_upper in ("DEBUG",):
                return DepartmentId.REASONING
            if mode_upper == "GENERAL_ASSISTANT":
                return DepartmentId.GENERAL

        # Intent label mapping
        if intent is not None:
            label = self._get_intent_label(intent)
            if label:
                mapped = INTENT_TO_DEPARTMENT.get(label)
                if mapped:
                    return mapped

        # Task type fallback
        if task_type:
            label = str(task_type).strip().lower()
            mapped = INTENT_TO_DEPARTMENT.get(label)
            if mapped:
                return mapped

        # Default
        return DepartmentId.GENERAL

    @staticmethod
    def _get_intent_label(intent: Any) -> Optional[str]:
        """Extract a label string from an intent result object."""
        if hasattr(intent, "label"):
            label = intent.label
            if hasattr(label, "value"):
                return str(label.value).strip().lower()
            return str(label).strip().lower()
        if isinstance(intent, dict):
            return str(intent.get("label", "")).strip().lower()
        return str(intent).strip().lower() if intent else None


# Singleton
department_router: DepartmentRouter = DepartmentRouter()


def classify_department(
    intent: Optional[Any] = None,
    task_type: Optional[str] = None,
    complexity_score: float = 0.0,
    preferred_provider: Optional[str] = None,
    preferred_model: Optional[str] = None,
    mode: Optional[str] = None,
) -> DepartmentSelection:
    """Convenience function: classify a message into a department."""
    return department_router.classify(
        intent=intent,
        task_type=task_type,
        complexity_score=complexity_score,
        preferred_provider=preferred_provider,
        preferred_model=preferred_model,
        mode=mode,
    )
