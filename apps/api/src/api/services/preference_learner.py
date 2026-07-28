"""
User Preference Learning.

Passively observes every response event and builds a per-user profile:
  - provider_affinity   — which LLMs a user keeps using vs. rates down
  - response_length_pref — concise vs. verbose, per intent label
  - intent_model_pref    — favourite model per intent type

All signals are aggregate statistics (no raw text stored).
New users get sensible defaults; the profile improves over time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()

# EWMA decay rates
_ALPHA_EXPLICIT = 0.20  # explicit +1/-1 feedback moves the needle harder
_ALPHA_IMPLICIT = 0.05  # implicit use is a weak positive

# Affinity threshold above which a provider is "preferred"
_AFFINITY_PROMOTE_THRESHOLD = 0.70

# Minimum observations before pinning an intent → model preference
_MIN_OBS_FOR_MODEL_PREF = 3

# Token buckets for response length preference
_CONCISE_MAX = 350
_VERBOSE_MIN = 800


def _bucket_tokens(tokens: int) -> str:
    if tokens <= _CONCISE_MAX:
        return "concise"
    if tokens >= _VERBOSE_MIN:
        return "verbose"
    return "medium"


def _default_profile() -> Dict[str, Any]:
    return {
        "provider_affinity": {},
        "response_length_pref": {"default": "medium"},
        "response_length_ewma": {},  # per-intent running average of completion_tokens
        "intent_model_pref": {},
        "observation_counts": {
            "total_responses": 0,
            "explicit_ratings": 0,
            "by_intent": {},
        },
        "last_updated": None,
    }


def _ewma(current: float, new_value: float, alpha: float) -> float:
    return (1 - alpha) * current + alpha * new_value


class PreferenceLearner:
    """
    Fire-and-forget learning loop. All public methods are async and fully
    self-contained — they load the profile, update it, and write it back.
    Failures are swallowed (never block the hot path).
    """

    # ------------------------------------------------------------------
    # Core learning method
    # ------------------------------------------------------------------

    async def record_response(
        self,
        user_id: str,
        provider_id: str,
        model: Optional[str],
        intent_label: str,
        completion_tokens: int,
        explicit_rating: Optional[int] = None,  # +1, -1, or None
    ) -> None:
        """
        Record one observation and update the user's preference profile.

        Meant to be called as asyncio.create_task(...) — never awaited on
        the hot path.
        """
        try:
            from api.storage.preferences_service import preferences_service  # noqa: PLC0415

            profile = await preferences_service.get_learned_preferences(user_id)
            profile = _merge_defaults(profile)

            provider_id = (provider_id or "").strip()
            intent_label = (intent_label or "unknown").strip()
            model = (model or "").strip() or None

            # ── 1. Provider affinity ──────────────────────────────────────
            if provider_id:
                current_affinity = profile["provider_affinity"].get(provider_id, 0.5)
                if explicit_rating == 1:
                    new_affinity = _ewma(current_affinity, 1.0, _ALPHA_EXPLICIT)
                elif explicit_rating == -1:
                    new_affinity = _ewma(current_affinity, 0.0, _ALPHA_EXPLICIT)
                else:
                    # Implicit use: weak positive signal
                    new_affinity = _ewma(current_affinity, 0.7, _ALPHA_IMPLICIT)
                profile["provider_affinity"][provider_id] = round(new_affinity, 4)

            # ── 2. Response length preference ─────────────────────────────
            if completion_tokens > 0 and explicit_rating != -1:
                ewma_key = intent_label
                current_ewma = profile["response_length_ewma"].get(ewma_key, completion_tokens)
                new_ewma = _ewma(current_ewma, completion_tokens, 0.15)
                profile["response_length_ewma"][ewma_key] = round(new_ewma, 1)
                profile["response_length_pref"][intent_label] = _bucket_tokens(int(new_ewma))

            # ── 3. Intent → model preference ─────────────────────────────
            if model and provider_id and intent_label != "unknown":
                intent_obs = profile["observation_counts"]["by_intent"].get(intent_label, 0)
                affinity = profile["provider_affinity"].get(provider_id, 0.5)
                if (
                    affinity >= _AFFINITY_PROMOTE_THRESHOLD
                    and intent_obs >= _MIN_OBS_FOR_MODEL_PREF
                    and explicit_rating != -1
                ):
                    profile["intent_model_pref"][intent_label] = model

            # ── 4. Observation counts ─────────────────────────────────────
            counts = profile["observation_counts"]
            counts["total_responses"] = counts.get("total_responses", 0) + 1
            if explicit_rating is not None:
                counts["explicit_ratings"] = counts.get("explicit_ratings", 0) + 1
            by_intent = counts.setdefault("by_intent", {})
            by_intent[intent_label] = by_intent.get(intent_label, 0) + 1

            profile["last_updated"] = datetime.now(timezone.utc).isoformat()

            await preferences_service.update_learned_preferences(user_id, profile)

        except Exception as exc:
            logger.warning("preference_learner_record_failed", user_id=user_id, error=str(exc))

    # ------------------------------------------------------------------
    # Profile read
    # ------------------------------------------------------------------

    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Return the learned preference profile; empty dict for new users."""
        try:
            from api.storage.preferences_service import preferences_service  # noqa: PLC0415

            return await preferences_service.get_learned_preferences(user_id)
        except Exception as exc:
            logger.warning("preference_learner_get_profile_failed", user_id=user_id, error=str(exc))
            return {}

    # ------------------------------------------------------------------
    # Routing re-ranking
    # ------------------------------------------------------------------

    async def apply_to_routing(
        self,
        user_id: str,
        candidates: List[str],
    ) -> List[str]:
        """
        Re-rank provider candidates by learned affinity.

        Providers with affinity >= threshold are floated to the front,
        preserving their relative order. The tail (low/unknown affinity)
        keeps its original ordering.
        Guarantees: never removes a candidate; never reorders below a single
        healthy provider.
        """
        if not candidates or not user_id:
            return candidates
        try:
            profile = await self.get_profile(user_id)
            affinities = profile.get("provider_affinity", {})
            if not affinities:
                return candidates

            preferred = [
                p for p in candidates if affinities.get(p, 0.5) >= _AFFINITY_PROMOTE_THRESHOLD
            ]
            rest = [p for p in candidates if p not in preferred]
            return preferred + rest
        except Exception as exc:
            logger.warning("preference_learner_routing_failed", user_id=user_id, error=str(exc))
            return candidates

    # ------------------------------------------------------------------
    # Convenience: preferred response length for an intent
    # ------------------------------------------------------------------

    async def get_length_pref(self, user_id: str, intent_label: str) -> str:
        """Return 'concise', 'medium', or 'verbose' for this user + intent."""
        try:
            profile = await self.get_profile(user_id)
            length_prefs = profile.get("response_length_pref", {})
            return length_prefs.get(intent_label) or length_prefs.get("default", "medium")
        except Exception:
            return "medium"


def _merge_defaults(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Fill in missing keys without overwriting existing values."""
    defaults = _default_profile()
    for key, default_val in defaults.items():
        if key not in profile:
            profile[key] = default_val
        elif isinstance(default_val, dict) and isinstance(profile[key], dict):
            for sub_key, sub_default in default_val.items():
                profile[key].setdefault(sub_key, sub_default)
    return profile


# Module-level singleton
preference_learner = PreferenceLearner()
