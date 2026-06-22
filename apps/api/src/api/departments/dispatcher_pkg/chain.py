"""Department provider-chain assembly and reordering helpers."""

from __future__ import annotations

import random
from typing import List, Tuple

import structlog

from ..models import DepartmentSelection
from ..registry import DEPARTMENT_REGISTRY

logger = structlog.get_logger()


def build_chain(selection: DepartmentSelection) -> List[Tuple[str, str]]:
    """Build the ordered provider chain to try for a department selection."""
    chain: List[Tuple[str, str]] = []

    if selection.resolved_provider:
        chain.append((selection.resolved_provider, selection.resolved_model))

    try:
        policy = DEPARTMENT_REGISTRY.get(selection.department_id)
        for pid, model_name in policy.fallback_providers:
            if pid != selection.resolved_provider:
                chain.append((pid, model_name))
    except KeyError:
        pass

    seen = set()
    deduped: List[Tuple[str, str]] = []
    for pid, model_name in chain:
        key = f"{pid}:{model_name}"
        if key not in seen:
            seen.add(key)
            deduped.append((pid, model_name))

    return reorder_chain_by_bandit(deduped, selection.department_id.value)


def reorder_chain_by_bandit(
    chain: List[Tuple[str, str]],
    task_type: str,
) -> List[Tuple[str, str]]:
    """Reorder provider chain using Thompson Sampling scores."""
    if len(chain) <= 1:
        return chain
    try:
        from api.routing.ml_router import _MIN_OBSERVATIONS, bandit_cache  # noqa: PLC0415

        scored: List[Tuple[float, int, str, str]] = []
        for idx, (pid, model_name) in enumerate(chain):
            state = bandit_cache.get(task_type, pid)
            if state.observation_count >= _MIN_OBSERVATIONS:
                score = random.betavariate(max(state.alpha, 0.01), max(state.beta, 0.01))
            else:
                score = 0.5 - idx * 0.001
            scored.append((score, idx, pid, model_name))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [(pid, model_name) for _, _, pid, model_name in scored]
    except Exception as exc:  # noqa: BLE001
        logger.debug("department_bandit_reorder_failed", task_type=task_type, error=str(exc))
        return chain
