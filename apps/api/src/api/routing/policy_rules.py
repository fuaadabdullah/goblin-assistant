"""
Declarative routing policy engine.

Administrators express routing behavior as rules in config/routing_policies.toml
instead of editing router code. Rules are evaluated against a request's
RoutingFeatures (+ optional metadata) before provider scoring, producing a
PolicyDecision that can:

  - restrict the candidate set to a tier or an explicit provider list
  - add a per-provider or per-tier score boost applied before softmax

Usage (see provider_selection.py for the live wiring):

    decision = policy_engine.evaluate(features, candidates, metadata=request_metadata)
    candidates = decision.apply_restriction(candidates)
    # ... after computing raw_scores ...
    decision.apply_boosts(raw_scores)
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import structlog

logger = structlog.get_logger()

_POLICIES_PATH = Path(__file__).resolve().parents[5] / "config" / "routing_policies.toml"


def _parse_toml(path: Path) -> dict:
    try:
        import tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        toml = importlib.import_module("toml")
        with open(path, "r", encoding="utf-8") as f:
            return toml.load(f)


@dataclass
class PolicyRule:
    """One declarative routing rule parsed from routing_policies.toml."""

    id: str
    description: str
    when: Dict[str, Any]
    action: Dict[str, Any]

    def matches(self, features: Any, metadata: Dict[str, Any]) -> bool:
        for key, expected in self.when.items():
            if key == "intent":
                if not _matches_str_or_list(getattr(features, "intent_label", None), expected):
                    return False
            elif key == "task_type":
                if not _matches_str_or_list(getattr(features, "task_type", None), expected):
                    return False
            elif key == "complexity_min":
                if float(getattr(features, "complexity_score", 0.0)) < float(expected):
                    return False
            elif key == "complexity_max":
                if float(getattr(features, "complexity_score", 0.0)) > float(expected):
                    return False
            elif key == "prompt_length_bucket_min":
                if int(getattr(features, "prompt_length_bucket", 0)) < int(expected):
                    return False
            elif key == "prompt_length_bucket_max":
                if int(getattr(features, "prompt_length_bucket", 0)) > int(expected):
                    return False
            elif key == "latency_sensitive_min":
                if float(getattr(features, "latency_sensitivity", 0.0)) < float(expected):
                    return False
            elif key == "metadata":
                if not isinstance(expected, dict):
                    return False
                for mk, mv in expected.items():
                    if metadata.get(mk) != mv:
                        return False
            else:
                logger.debug("policy_rule_unknown_condition", rule_id=self.id, condition=key)
        return True


def _matches_str_or_list(value: Optional[str], expected: Any) -> bool:
    if value is None:
        return False
    if isinstance(expected, list):
        return value in expected
    return value == expected


@dataclass
class PolicyDecision:
    """Result of evaluating all rules against one request."""

    restrict_to: Optional[Set[str]] = None
    boosts: Dict[str, float] = field(default_factory=dict)
    matched_rules: List[str] = field(default_factory=list)

    def apply_restriction(self, candidates: List[str]) -> List[str]:
        """Filter candidates to the restricted set, unless that would empty the list."""
        if not self.restrict_to:
            return candidates
        filtered = [c for c in candidates if c in self.restrict_to]
        # A restriction that matches nothing in the current candidate set is a
        # misconfiguration or a temporarily-unavailable tier — never route to
        # an empty candidate list, fall back to the unrestricted set instead.
        return filtered or candidates

    def apply_boosts(self, raw_scores: Dict[str, float]) -> None:
        for provider_id, boost in self.boosts.items():
            if provider_id in raw_scores:
                raw_scores[provider_id] += boost


class PolicyEngine:
    """Loads declarative rules and evaluates them into routing decisions."""

    def __init__(self) -> None:
        self._rules: List[PolicyRule] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._rules = self._load_rules()
        self._loaded = True

    def reload(self) -> None:
        """Force a re-read of routing_policies.toml (e.g. after an admin edit)."""
        self._rules = self._load_rules()
        self._loaded = True

    def _load_rules(self) -> List[PolicyRule]:
        if not _POLICIES_PATH.exists():
            return []
        try:
            parsed = _parse_toml(_POLICIES_PATH)
        except Exception as exc:
            logger.warning("policy_rules_load_failed", error=str(exc))
            return []

        rules: List[PolicyRule] = []
        for raw in parsed.get("rules", []):
            if not isinstance(raw, dict) or "id" not in raw:
                continue
            rules.append(
                PolicyRule(
                    id=str(raw["id"]),
                    description=str(raw.get("description", "")),
                    when=dict(raw.get("when", {})),
                    action=dict(raw.get("action", {})),
                )
            )
        return rules

    def evaluate(
        self,
        features: Any,
        candidates: List[str],
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        self._ensure_loaded()
        metadata = metadata or {}
        decision = PolicyDecision()

        for rule in self._rules:
            try:
                if not rule.matches(features, metadata):
                    continue
            except Exception as exc:
                logger.debug("policy_rule_match_failed", rule_id=rule.id, error=str(exc))
                continue

            decision.matched_rules.append(rule.id)
            self._apply_action(rule, decision, candidates)

        return decision

    def _apply_action(
        self, rule: PolicyRule, decision: PolicyDecision, candidates: List[str]
    ) -> None:
        from .policy_engine import tier_router  # noqa: PLC0415

        action = rule.action

        if "restrict_tier" in action:
            tier_providers = set(tier_router.providers_for_tier(str(action["restrict_tier"])))
            decision.restrict_to = (decision.restrict_to or set(candidates)) & tier_providers

        if "restrict_providers" in action:
            explicit = set(action["restrict_providers"])
            decision.restrict_to = (decision.restrict_to or set(candidates)) & explicit

        if "prefer_tier" in action:
            boost = float(action.get("boost", 0.15))
            for pid in tier_router.providers_for_tier(str(action["prefer_tier"])):
                decision.boosts[pid] = decision.boosts.get(pid, 0.0) + boost

        boost_providers = action.get("boost_providers")
        if isinstance(boost_providers, dict):
            for pid, amount in boost_providers.items():
                decision.boosts[pid] = decision.boosts.get(pid, 0.0) + float(amount)


policy_engine = PolicyEngine()
