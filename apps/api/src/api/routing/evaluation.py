"""
Routing evaluation harness — GoblinOS routing benchmark.

Scope, deliberately: this benchmarks the ROUTER'S DECISIONS (did it pick the
tier/provider the policy rules say it should, at what cost), not the QUALITY
OF MODEL OUTPUT. It makes zero live provider calls, so it's free and fast
enough to run in CI as a regression guard on routing_policies.toml.

It answers: "is the router doing what we designed it to do, and what does
that cost look like across providers?" It does NOT answer: "does a review
chain improve coding accuracy by N%?" — that requires dispatching real
prompts to real providers and judging the responses, which is a separate,
funded piece of work (tracked as a precondition for GoblinOS v0.3 multi-model
orchestration — see BENCHMARK_SUITE docstring below for why that matters).

Two complementary views:
  - run_routing_benchmark()       — synthetic cases vs. the live policy engine
  - production_reliability_snapshot() — real success-rate/latency from traffic
    already flowing through the dispatcher (router_registry.registry), plus a
    pointer to feedback_service for thumbs-up/down rates by provider.
"""

from __future__ import annotations

import importlib
import random
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from unittest.mock import patch

# Bandit exploration noise (see feature_router.score_provider) means a single
# scoring draw is not deterministic — at low observation_count the router is
# intentionally exploring. Tier expectations are therefore checked as a
# win-rate over repeated trials, not a single-draw assertion.
_TIER_CHECK_TRIALS = 25
_TIER_CHECK_MIN_WIN_RATE = 0.5
_BENCHMARK_SEED = 20260717  # fixed seed so CI runs are reproducible

from .feature_extractor import ProviderFeatures, RoutingFeatures
from .policy_engine import tier_router
from .policy_rules import policy_engine
from .provider_selection import get_explanation, provider_selection_model

_PROVIDERS_TOML_PATH = Path(__file__).resolve().parents[5] / "config" / "providers.toml"

# All providers referenced anywhere in the tier map — the representative
# candidate pool for the benchmark. Kept in sync with policy_engine.py's
# ModelTierRouter so a benchmark failure means the tiers/rules disagree with
# each other, not that the benchmark invented its own taxonomy.
_ALL_TIER_PROVIDERS: List[str] = sorted(
    {pid for providers in tier_router.TIER_PROVIDERS.values() for pid in providers}
)


@dataclass
class BenchmarkCase:
    """One synthetic routing scenario with an expectation to check against it."""

    id: str
    description: str
    features: RoutingFeatures
    metadata: Dict[str, Any] = field(default_factory=dict)
    candidates: Optional[List[str]] = None  # defaults to _ALL_TIER_PROVIDERS
    expect_matched_policy: Optional[str] = None  # policy id that must fire
    expect_provider_in_tier: Optional[str] = None  # chosen provider must be in this tier
    expect_no_policy_match: bool = False  # sanity/baseline case — no rule should fire


BENCHMARK_SUITE: List[BenchmarkCase] = [
    BenchmarkCase(
        id="trivial_arithmetic",
        description="'What is 2+2?' — trivial request should demote to the fast/cheap tier.",
        features=RoutingFeatures(
            prompt_length_bucket=0,
            task_type="chat",
            complexity_score=0.02,
            conversation_turn=0,
            intent_label="chat",
            intent_confidence=0.9,
        ),
        expect_matched_policy="trivial_request",
        expect_provider_in_tier="fast",
    ),
    BenchmarkCase(
        id="expert_refactor",
        description="Deep multi-file refactor question — should boost toward the best tier.",
        features=RoutingFeatures(
            prompt_length_bucket=2,
            task_type="coding",
            complexity_score=0.85,
            conversation_turn=2,
            intent_label="reasoning",
            intent_confidence=0.9,
        ),
        expect_matched_policy="expert_request",
        expect_provider_in_tier="best",
    ),
    BenchmarkCase(
        id="coding_task",
        description="Coding-intent request should trigger the Anthropic coding boost.",
        features=RoutingFeatures(
            prompt_length_bucket=1,
            task_type="coding",
            complexity_score=0.5,
            conversation_turn=0,
            intent_label="coding",
            intent_confidence=0.9,
        ),
        expect_matched_policy="coding_boost",
    ),
    BenchmarkCase(
        id="confidential_request",
        description="Confidential metadata flag should restrict routing to the local tier.",
        features=RoutingFeatures(
            prompt_length_bucket=1,
            task_type="chat",
            complexity_score=0.4,
            conversation_turn=0,
            intent_label="chat",
            intent_confidence=0.7,
        ),
        metadata={"confidential": True},
        expect_matched_policy="confidential",
        expect_provider_in_tier="local",
    ),
    BenchmarkCase(
        id="huge_context_doc",
        description="Very long prompt should boost large-context-window providers.",
        features=RoutingFeatures(
            prompt_length_bucket=3,
            task_type="research",
            complexity_score=0.6,
            conversation_turn=1,
            intent_label="research",
            intent_confidence=0.8,
        ),
        expect_matched_policy="huge_context",
    ),
    BenchmarkCase(
        id="normal_chat_baseline",
        description="Ordinary mid-length chat — no policy should fire (baseline sanity check).",
        features=RoutingFeatures(
            prompt_length_bucket=1,
            task_type="chat",
            complexity_score=0.4,
            conversation_turn=1,
            intent_label="chat",
            intent_confidence=0.6,
        ),
        expect_no_policy_match=True,
    ),
]


@dataclass
class CaseResult:
    case_id: str
    description: str
    matched_policies: List[str]
    chosen_provider: Optional[str]
    chosen_score: float
    candidate_scores: Dict[str, float]
    tier_win_rate: Optional[float]
    passed: bool
    reason: str
    stage_durations_ms: Dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    cases: List[CaseResult]
    pass_rate: float
    cost_quality_frontier: List[Dict[str, Any]]


def _check_case(
    case: BenchmarkCase,
    matched: List[str],
    tier_win_rate: Optional[float],
) -> tuple:
    if case.expect_no_policy_match:
        if matched:
            return False, f"expected no policy match, got {matched}"
        return True, "no policy matched, as expected"

    if case.expect_matched_policy and case.expect_matched_policy not in matched:
        return False, f"expected policy '{case.expect_matched_policy}' to fire, got {matched}"

    if case.expect_provider_in_tier and tier_win_rate is not None:
        if tier_win_rate < _TIER_CHECK_MIN_WIN_RATE:
            return (
                False,
                f"expected tier '{case.expect_provider_in_tier}' to win >= "
                f"{_TIER_CHECK_MIN_WIN_RATE:.0%} of {_TIER_CHECK_TRIALS} trials, "
                f"got {tier_win_rate:.0%}",
            )

    return True, "matched expectations"


def _tier_win_rate(case: BenchmarkCase, candidates: List[str]) -> Optional[float]:
    """Fraction of repeated scoring trials where the winner lands in the
    expected tier. Bandit exploration noise means a single draw isn't
    representative — see module-level trial constants."""
    if not case.expect_provider_in_tier:
        return None
    tier_providers = set(tier_router.providers_for_tier(case.expect_provider_in_tier))
    wins = 0
    for _ in range(_TIER_CHECK_TRIALS):
        trial = provider_selection_model.score(
            candidates,
            case.features,
            task_type=case.features.task_type,
            metadata=case.metadata,
        )
        if trial and trial[0].provider_id in tier_providers:
            wins += 1
    return wins / _TIER_CHECK_TRIALS


def _neutral_provider_features(
    candidates: List[str],
    provider_costs: Dict[str, Any],
    registry_snapshot: Dict[str, Any],
    health_availability: Optional[Dict[str, bool]] = None,
) -> Dict[str, ProviderFeatures]:
    """Every candidate starts from the same neutral, healthy prior."""
    del provider_costs, registry_snapshot, health_availability
    return {
        pid: ProviderFeatures(
            provider_id=pid, success_rate=0.5, norm_latency=0.5, norm_cost=0.5, is_healthy=True
        )
        for pid in candidates
    }


@contextmanager
def _isolated_benchmark_environment() -> Iterator[None]:
    """Neutralise every source of environment-dependence in provider scoring.

    Two things would otherwise leak into the benchmark and make it depend on
    this machine/process's history rather than the routing logic itself:

    1. Provider health + registry stats (success_rate, latency, cost) both
       flow through feature_extractor.extract_providers(). Health is injected
       as a routing snapshot, while registry stats come from the on-disk
       routing_registry.db, which accumulates cross-process noise, including
       from test fixtures (provider ids like "primary", "alpha",
       "fast_cheap" leak in from unit tests pointed at the same default
       path). Patching extract_providers itself keeps benchmark inputs
       deterministic without reaching into health or registry internals.

    2. feature_router's learned weights — FeatureWeights.observation_count is
       a module-level singleton mutated by ANY code path that calls
       record_outcome() for a given task_type, including other tests in the
       same process. observation_count controls the bandit's
       exploration/exploitation ratio, so a nonzero count means results
       depend on execution order/history instead of the seeded RNG alone —
       this was the actual source of the non-reproducible win-rates observed
       across repeated runs before this was added. Reset to a fresh
       WeightsCache so every benchmark run starts from the same
       zero-observation ("brand new system") state.

    Net effect: the benchmark isolates exactly what it claims to measure —
    policy rules + bandit exploration under the fixed seed — from ambient
    machine/process/test state.
    """
    from .feature_router import WeightsCache

    with (
        patch(
            "api.routing.provider_selection.feature_extractor.extract_providers",
            side_effect=_neutral_provider_features,
        ),
        patch("api.routing.feature_router.feature_router._cache", WeightsCache()),
    ):
        yield


def run_routing_benchmark(
    suite: Optional[List[BenchmarkCase]] = None,
) -> BenchmarkReport:
    """Run the synthetic benchmark suite through the real policy engine + scorer.

    Makes no network calls — this is pure in-process scoring, safe for CI.
    """
    random.seed(_BENCHMARK_SEED)
    suite = suite if suite is not None else BENCHMARK_SUITE
    results: List[CaseResult] = []
    all_scores: Dict[str, List[float]] = {}

    with _isolated_benchmark_environment():
        results, all_scores = _run_cases(suite)

    pass_rate = sum(1 for r in results if r.passed) / len(results) if results else 0.0
    frontier = _cost_quality_frontier(all_scores)

    return BenchmarkReport(
        cases=results, pass_rate=round(pass_rate, 4), cost_quality_frontier=frontier
    )


def _run_cases(
    suite: List[BenchmarkCase],
) -> Tuple[List[CaseResult], Dict[str, List[float]]]:
    results: List[CaseResult] = []
    all_scores: Dict[str, List[float]] = {}

    for case in suite:
        candidates = case.candidates or list(_ALL_TIER_PROVIDERS)
        routing_id = f"benchmark:{case.id}"
        scored = provider_selection_model.score(
            candidates,
            case.features,
            task_type=case.features.task_type,
            metadata=case.metadata,
            routing_id=routing_id,
        )
        decision = policy_engine.evaluate(case.features, candidates, metadata=case.metadata)
        win_rate = _tier_win_rate(case, candidates)
        explanation = get_explanation(routing_id) or {}
        stage_durations = _stage_durations_from_explanation(explanation)

        chosen = scored[0] if scored else None
        for s in scored:
            all_scores.setdefault(s.provider_id, []).append(s.score)

        passed, reason = _check_case(case, decision.matched_rules, win_rate)
        results.append(
            CaseResult(
                case_id=case.id,
                description=case.description,
                matched_policies=decision.matched_rules,
                chosen_provider=chosen.provider_id if chosen else None,
                chosen_score=chosen.score if chosen else 0.0,
                candidate_scores={s.provider_id: round(s.score, 4) for s in scored},
                tier_win_rate=win_rate,
                passed=passed,
                reason=reason,
                stage_durations_ms=stage_durations,
            )
        )

    return results, all_scores


def _stage_durations_from_explanation(explanation: Dict[str, Any]) -> Dict[str, float]:
    trace = explanation.get("routing_trace")
    if not isinstance(trace, list):
        return {}

    durations: Dict[str, float] = {}
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        stage = entry.get("stage")
        if not isinstance(stage, str) or not stage:
            continue
        try:
            durations[stage] = float(entry.get("duration_ms", 0.0))
        except (TypeError, ValueError):
            durations[stage] = 0.0
    return durations


# ---------------------------------------------------------------------------
# Cost-vs-score frontier
# ---------------------------------------------------------------------------


def _load_provider_costs() -> Dict[str, tuple]:
    """Read (input_per1k, output_per1k) straight from providers.toml — no
    dispatcher/live-provider dependency, so this stays usable in CI."""
    if not _PROVIDERS_TOML_PATH.exists():
        return {}
    try:
        import tomllib

        with open(_PROVIDERS_TOML_PATH, "rb") as f:
            parsed = tomllib.load(f)
    except ImportError:
        toml = importlib.import_module("toml")
        with open(_PROVIDERS_TOML_PATH, "r", encoding="utf-8") as f:
            parsed = toml.load(f)
    except Exception:
        return {}

    costs: Dict[str, tuple] = {}
    for pid, raw in parsed.get("providers", {}).items():
        if not isinstance(raw, dict):
            continue
        costs[pid] = (
            float(raw.get("cost_input_per1k", 0.0)),
            float(raw.get("cost_output_per1k", 0.0)),
        )
    return costs


def _cost_quality_frontier(all_scores: Dict[str, List[float]]) -> List[Dict[str, Any]]:
    """Per-provider: average router-assigned score across benchmark cases vs.
    published $/1k-token pricing. NOTE: 'score' here is the router's own
    confidence signal (success-rate/latency/cost priors + policy boosts), not
    an independent measurement of response quality — see module docstring."""
    costs = _load_provider_costs()
    frontier = []
    for pid, scores in all_scores.items():
        input_cost, output_cost = costs.get(pid, (0.0, 0.0))
        frontier.append(
            {
                "provider_id": pid,
                "avg_router_score": round(sum(scores) / len(scores), 4),
                "cost_input_per1k": input_cost,
                "cost_output_per1k": output_cost,
            }
        )
    frontier.sort(key=lambda r: r["avg_router_score"], reverse=True)
    return frontier


# ---------------------------------------------------------------------------
# Production reliability snapshot — real traffic, not synthetic
# ---------------------------------------------------------------------------


def production_reliability_snapshot() -> Dict[str, Dict[str, float]]:
    """Real success-rate/latency per provider from the live routing registry.

    This reflects actual dispatched traffic (router_registry.registry is
    updated by the dispatcher on every real provider call), unlike the
    synthetic benchmark above. For user-satisfaction signal (thumbs up/down
    by provider/task_type), see api.services.feedback_service.get_feedback_stats
    — deliberately not duplicated here since it already persists to Supabase
    and has its own /feedback/stats endpoint.
    """
    from .router_registry import registry

    snapshot = registry.snapshot()
    return {
        pid: {
            "success_rate": round(float(stats.get("success_rate", 1.0)), 4),
            "ewma_latency_ms": round(float(stats.get("ewma_latency_ms", 0.0)), 1),
        }
        for pid, stats in snapshot.items()
    }
