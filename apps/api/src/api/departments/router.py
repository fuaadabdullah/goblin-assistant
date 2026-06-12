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

# Lazy import to avoid circular dependencies at module load time.
# resolved on first call to classify().
_learned_router = None


def _get_learned_router():
    global _learned_router
    if _learned_router is None:
        try:
            from api.routing.learned_department_router import (  # noqa: PLC0415
                learned_department_router,
            )
            _learned_router = learned_department_router
        except Exception:
            pass
    return _learned_router


_MODE_MAP = {
    "RESEARCH": DepartmentId.RESEARCH,
    "DEEP_RESEARCH": DepartmentId.RESEARCH,
    "DEBUG": DepartmentId.REASONING,
    "GENERAL_ASSISTANT": DepartmentId.GENERAL,
}


def _dept_from_mode(mode: Optional[str]) -> Optional[DepartmentId]:
    """Return a DepartmentId for an explicit mode override, or None."""
    if not mode:
        return None
    return _MODE_MAP.get(str(mode).strip().upper())


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
        routing_features: Optional[Any] = None,
        request_id: Optional[str] = None,
    ) -> DepartmentSelection:
        """Determine the best department for a request.

        Args:
            intent: IntentResult from the intent classifier (has .label and .confidence).
            task_type: Optional explicit task type string.
            complexity_score: 0.0–1.0 complexity from feature extractor.
            preferred_provider: Internal provider override (for migration compat).
            preferred_model: Internal model override (for migration compat).
            mode: Explicit mode string (e.g. "DEEP_RESEARCH", "GENERAL_ASSISTANT").
            routing_features: RoutingFeatures from the feature extractor; when provided,
                the learned department router scores against these.
            request_id: Optional request ID for caching features for feedback attribution.

        Returns:
            DepartmentSelection with the chosen department, reason, and
            resolved provider (internal) ready for dispatch.
        """
        # ── Step 1: Determine department from intent label (rule-based) ──
        rule_dept_id = self._department_from_intent(intent, task_type, mode)
        reason_parts: list[str] = []

        # ── Step 1b: Optionally score via the learned router ─────────────
        dept_id, department_confidence = self._apply_learned_router(
            rule_dept_id, routing_features, request_id, reason_parts
        )

        # ── Step 2: Determine quality tier from complexity ────────────────
        tier = quality_tier_for_complexity(complexity_score)
        if dept_id == DepartmentId.RECALL:
            tier = DepartmentQualityTier.SPEED
        if dept_id == DepartmentId.RESEARCH:
            tier = DepartmentQualityTier.QUALITY

        # ── Step 3: Resolve provider from department policy ───────────────
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
            department_confidence=department_confidence,
        )

    def _apply_learned_router(
        self,
        rule_dept_id: DepartmentId,
        routing_features: Optional[Any],
        request_id: Optional[str],
        reason_parts: list,
    ) -> tuple:
        """Run the learned router and return (dept_id, confidence).

        In shadow mode the rule-based dept_id is returned unchanged and
        divergences are debug-logged.  In live mode the learned pick is used.
        """
        if routing_features is None:
            return rule_dept_id, 0.0
        try:
            lr = _get_learned_router()
            if lr is None:
                return rule_dept_id, 0.0
            learned_dept_str, confidence = lr.select(routing_features, request_id=request_id)
            if lr.is_live:
                return self._resolve_learned_dept(learned_dept_str, rule_dept_id, confidence, reason_parts)
            # Shadow mode
            if learned_dept_str != rule_dept_id.value:
                logger.debug(
                    "department_router_shadow_divergence",
                    rule=rule_dept_id.value,
                    learned=learned_dept_str,
                    confidence=confidence,
                )
            return rule_dept_id, confidence
        except Exception as exc:
            logger.debug("department_router_learned_failed error=%s", exc)
            return rule_dept_id, 0.0

    @staticmethod
    def _resolve_learned_dept(
        learned_dept_str: str,
        fallback: DepartmentId,
        confidence: float,
        reason_parts: list,
    ) -> tuple:
        """Parse the learned dept string into a DepartmentId, falling back on error."""
        try:
            dept_id = DepartmentId(learned_dept_str)
            reason_parts.append("learned")
            return dept_id, confidence
        except ValueError:
            return fallback, 0.0

    def _department_from_intent(
        self,
        intent: Optional[Any],
        task_type: Optional[str],
        mode: Optional[str],
    ) -> DepartmentId:
        """Map intent/type/mode to a DepartmentId."""
        mode_dept = _dept_from_mode(mode)
        if mode_dept is not None:
            return mode_dept

        if intent is not None:
            label = self._get_intent_label(intent)
            mapped = INTENT_TO_DEPARTMENT.get(label or "")
            if mapped:
                return mapped

        if task_type:
            mapped = INTENT_TO_DEPARTMENT.get(str(task_type).strip().lower())
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
    routing_features: Optional[Any] = None,
    request_id: Optional[str] = None,
) -> DepartmentSelection:
    """Convenience function: classify a message into a department."""
    return department_router.classify(
        intent=intent,
        task_type=task_type,
        complexity_score=complexity_score,
        preferred_provider=preferred_provider,
        preferred_model=preferred_model,
        mode=mode,
        routing_features=routing_features,
        request_id=request_id,
    )
