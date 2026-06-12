"""
Thompson Sampling bandit router for provider selection.

Maintains a Beta(alpha, beta) distribution per (task_type, provider_id) pair.
- alpha tracks successes + positive user ratings
- beta  tracks failures  + negative user ratings

When a (task_type, provider_id) pair has fewer than BANDIT_MIN_OBSERVATIONS
outcomes, the pair falls through to HybridRouter (cold-start safe).

State is held in memory (BanditCache) and persisted to Supabase
routing_bandit_state asynchronously. On process restart, state is restored
from Supabase via restore_bandit_state().
"""

from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_MIN_OBSERVATIONS = int(os.getenv("BANDIT_MIN_OBSERVATIONS", "3"))


@dataclass
class BanditState:
    task_type: str
    provider_id: str
    alpha: float = 1.0  # Beta shape: successes + positive ratings + prior
    beta: float = 1.0  # Beta shape: failures  + negative ratings + prior
    observation_count: int = 0


class BanditCache:
    """In-memory store of Beta distribution parameters per (task_type, provider_id)."""

    def __init__(self) -> None:
        self._states: Dict[Tuple[str, str], BanditState] = {}
        self._loaded: bool = False

    def get(self, task_type: str, provider_id: str) -> BanditState:
        key = (task_type, provider_id)
        if key not in self._states:
            self._states[key] = BanditState(task_type=task_type, provider_id=provider_id)
        return self._states[key]

    def update(
        self,
        task_type: str,
        provider_id: str,
        *,
        success: Optional[bool],
        rating: Optional[int] = None,
    ) -> BanditState:
        """
        Update Beta parameters in-place.

        success=True  → alpha += 1.0 (confirmed good outcome)
        success=False → beta  += 1.0 (confirmed bad outcome)
        success=None  → rating-only update (no observation_count increment)
        rating=+1     → alpha += 0.5 (user liked it, but noisier signal)
        rating=-1     → beta  += 0.5 (user disliked it)
        """
        state = self.get(task_type, provider_id)

        if success is True:
            state.alpha += 1.0
            state.observation_count += 1
        elif success is False:
            state.beta += 1.0
            state.observation_count += 1

        if rating == 1:
            state.alpha += 0.5
        elif rating == -1:
            state.beta += 0.5

        return state

    def has_sufficient_data(self, task_type: str, provider_id: str, min_obs: int) -> bool:
        key = (task_type, provider_id)
        state = self._states.get(key)
        return state is not None and state.observation_count >= min_obs

    def mark_loaded(self) -> None:
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded


class BanditRouter:
    """
    Thompson Sampling provider ranker.

    For providers with sufficient data: sample random.betavariate(alpha, beta)
    — higher sample → higher rank (better estimated quality).

    For providers without enough data: delegate to HybridRouter, then
    interleave the two ranked lists so unexplored providers still get tried.
    """

    def __init__(
        self,
        cache: BanditCache,
        fallback: object,  # HybridRouter — avoid circular import at definition time
        min_observations: int = _MIN_OBSERVATIONS,
    ) -> None:
        self._cache = cache
        self._fallback = fallback
        self._min_observations = min_observations

    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, tuple],
        *,
        task_type: str,
        request_id: Optional[str] = None,
        request: "Optional[object]" = None,  # RoutingFeatures when available
    ) -> List[str]:
        """Return candidates sorted best-first.

        When `request` (RoutingFeatures) is supplied, delegates to FeatureRouter
        for full contextual ML scoring. Falls back to Thompson Sampling +
        HybridRouter when features are unavailable.
        """
        if not candidates:
            return candidates

        # Feature-based path: use full ML scoring when request features are present
        if request is not None:
            try:
                from api.routing.feature_router import feature_router  # noqa: PLC0415

                return feature_router.rank(
                    candidates,
                    provider_costs,
                    task_type=task_type,
                    request=request,
                    request_id=request_id,
                )
            except Exception as exc:
                logger.debug("feature_router_rank_failed falling_back error=%s", exc)

        # Pure Thompson Sampling path (cold-start / fallback)
        bandit_set = [
            p
            for p in candidates
            if self._cache.has_sufficient_data(task_type, p, self._min_observations)
        ]
        fallback_set = [p for p in candidates if p not in set(bandit_set)]

        # Sample from Beta distribution for bandit candidates (higher = better)
        bandit_scored = sorted(
            bandit_set,
            key=lambda p: _sample_beta(self._cache.get(task_type, p)),
            reverse=True,
        )

        # HybridRouter ranks fallback candidates by latency/cost score (lower = better)
        fallback_ranked: List[str] = []
        if fallback_set:
            try:
                fallback_ranked = self._fallback.rank(fallback_set, provider_costs)
            except Exception:
                fallback_ranked = fallback_set

        # Interleave: bandit first, then fallback, ensuring explored providers lead
        # but unexplored ones are never permanently buried
        result: List[str] = []
        b_idx, f_idx = 0, 0
        while b_idx < len(bandit_scored) or f_idx < len(fallback_ranked):
            if b_idx < len(bandit_scored):
                result.append(bandit_scored[b_idx])
                b_idx += 1
            if f_idx < len(fallback_ranked):
                result.append(fallback_ranked[f_idx])
                f_idx += 1

        return result

    def record_outcome(
        self,
        *,
        request_id: str,
        task_type: str,
        provider_id: str,
        was_selected: bool,
        latency_ms: Optional[float],
        cost_usd: Optional[float],
        success: bool,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Record a routing outcome — updates cache and fires Supabase writes."""
        self._cache.update(task_type, provider_id, success=success)
        updated_state = self._cache.get(task_type, provider_id)

        _fire_routing_event(
            request_id=request_id,
            task_type=task_type,
            provider_id=provider_id,
            was_selected=was_selected,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            session_id=session_id,
            user_id=user_id,
        )
        _fire_bandit_state_upsert(updated_state)

        # Also update the feature router's learned weights if features were cached
        try:
            from api.routing.feature_router import feature_router  # noqa: PLC0415

            feature_router.record_outcome_by_request_id(
                request_id=request_id,
                task_type=task_type,
                provider_id=provider_id,
                success=success,
            )
        except Exception as exc:
            logger.debug("feature_router_outcome_failed error=%s", exc)


# ---------------------------------------------------------------------------
# Supabase persistence helpers
# ---------------------------------------------------------------------------


def _fire_routing_event(
    *,
    request_id: str,
    task_type: str,
    provider_id: str,
    was_selected: bool,
    latency_ms: Optional[float],
    cost_usd: Optional[float],
    success: bool,
    session_id: Optional[str],
    user_id: Optional[str],
) -> None:
    try:
        from api.providers.supabase_events import _fire, _post  # noqa: PLC0415

        payload = {
            "request_id": request_id,
            "task_type": task_type,
            "provider_id": provider_id,
            "was_selected": was_selected,
            "success": success,
        }
        if latency_ms is not None:
            payload["latency_ms"] = int(latency_ms)
        if cost_usd is not None:
            payload["cost_usd"] = str(cost_usd)
        if session_id:
            payload["session_id"] = session_id
        if user_id:
            payload["user_id"] = user_id

        _fire(_post("routing_events", payload, "return=minimal"))
    except Exception as exc:
        logger.debug("bandit_routing_event_write_failed error=%s", exc)


def _fire_bandit_state_upsert(state: BanditState) -> None:
    try:
        from api.providers.supabase_events import (  # noqa: PLC0415
            _HEADERS,
            _REST,
            _fire,
            _get_client,
        )

        async def _upsert() -> None:
            if not _REST:
                return
            try:
                payload = {
                    "task_type": state.task_type,
                    "provider_id": state.provider_id,
                    "alpha": state.alpha,
                    "beta": state.beta,
                    "observation_count": state.observation_count,
                    "last_updated_at": "now()",
                }
                await _get_client().post(
                    f"{_REST}/routing_bandit_state",
                    headers={
                        **_HEADERS,
                        "Prefer": "resolution=merge-duplicates,return=minimal",
                    },
                    json=payload,
                )
            except Exception as exc:
                logger.debug("bandit_state_upsert_failed error=%s", exc)

        _fire(_upsert())
    except Exception as exc:
        logger.debug("bandit_state_upsert_schedule_failed error=%s", exc)


# ---------------------------------------------------------------------------
# Startup restore
# ---------------------------------------------------------------------------


async def restore_bandit_state(cache: BanditCache) -> None:
    """
    Load routing_bandit_state from Supabase into the in-memory cache.
    Called once at process startup. No-op when Supabase is not configured.
    """
    try:
        from api.providers.supabase_events import (  # noqa: PLC0415
            _ENABLED,
            _HEADERS,
            _REST,
            _get_client,
        )

        if not _ENABLED:
            cache.mark_loaded()
            return

        resp = await _get_client().get(
            f"{_REST}/routing_bandit_state",
            headers={**_HEADERS, "Accept": "application/json"},
            params={"select": "task_type,provider_id,alpha,beta,observation_count"},
        )
        rows = resp.json() if resp.status_code == 200 else []
        if isinstance(rows, list):
            for row in rows:
                try:
                    state = BanditState(
                        task_type=row["task_type"],
                        provider_id=row["provider_id"],
                        alpha=float(row.get("alpha", 1.0)),
                        beta=float(row.get("beta", 1.0)),
                        observation_count=int(row.get("observation_count", 0)),
                    )
                    cache._states[(state.task_type, state.provider_id)] = state
                except (KeyError, ValueError, TypeError):
                    continue
            logger.info("bandit_state_restored rows=%d", len(cache._states))

    except Exception as exc:
        logger.warning("bandit_state_restore_failed error=%s", exc)

    cache.mark_loaded()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sample_beta(state: BanditState) -> float:
    """Sample from Beta(alpha, beta) using stdlib random — no numpy needed."""
    try:
        return random.betavariate(max(state.alpha, 0.01), max(state.beta, 0.01))
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

bandit_cache = BanditCache()


# Import HybridRouter lazily at instantiation time so this module can be
# imported before router_strategies is fully initialised.
def _make_bandit_router() -> BanditRouter:
    from api.routing.router_strategies import hybrid_router  # noqa: PLC0415

    return BanditRouter(
        cache=bandit_cache,
        fallback=hybrid_router,
        min_observations=_MIN_OBSERVATIONS,
    )


bandit_router: BanditRouter = _make_bandit_router()
