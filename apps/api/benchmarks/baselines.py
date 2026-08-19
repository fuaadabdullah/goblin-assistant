"""
Strategy definitions for the benchmark baselines.

Each strategy resolves to a (provider_id, model) pair for a given prompt.
The dispatcher is imported lazily so this module can be imported without
starting the full FastAPI app.
"""

from __future__ import annotations

import random
from typing import Optional


def _dispatcher():
    from api.providers.dispatcher import dispatcher  # noqa: PLC0415

    return dispatcher


def _routable_candidates(candidates: list[str]) -> list[str]:
    d = _dispatcher()
    routable: list[str] = []
    for provider_id in candidates:
        if not d.is_configured(provider_id):
            continue
        provider = d._ensure_provider(provider_id)
        if provider is None:
            continue
        should_attempt = getattr(provider, "should_attempt", None)
        if callable(should_attempt):
            try:
                if should_attempt(canary=False):
                    routable.append(provider_id)
                    continue
            except Exception:
                pass
        if getattr(provider, "is_available", lambda: False)():
            routable.append(provider_id)
    return routable or [candidate for candidate in candidates if d.is_configured(candidate)]


def cheapest_provider() -> tuple[str, Optional[str]]:
    """Return the first provider in cheapest-cost order."""
    d = _dispatcher()
    order = _routable_candidates(d._cheapest_order())
    if not order:
        raise RuntimeError("No configured providers found for cheapest strategy")
    pid = order[0]
    cfg = d._configs.get(pid, {})
    return pid, cfg.get("default_model")


def strongest_provider() -> tuple[str, Optional[str]]:
    """
    Return the provider most likely to produce the highest-quality response.

    Uses the dispatcher's capability ranking for 'reasoning' (the most
    demanding capability) and picks the first result. This tends to select
    the most capable configured model (Opus, GPT-4o, etc.).
    """
    d = _dispatcher()
    top = _routable_candidates(
        d.top_providers_for("reasoning", prefer_cost=False, limit=6),
    )
    if top:
        pid = top[0]
        cfg = d._configs.get(pid, {})
        return pid, cfg.get("default_model")
    # Fallback: pick the first in hybrid order (quality-aware)
    order = _routable_candidates(d._hybrid_order())
    if not order:
        raise RuntimeError("No configured providers found for strongest strategy")
    pid = order[0]
    cfg = d._configs.get(pid, {})
    return pid, cfg.get("default_model")


def random_provider() -> tuple[str, Optional[str]]:
    """Return a randomly chosen configured provider."""
    d = _dispatcher()
    providers = _routable_candidates(
        [p["id"] for p in d.list_providers(include_hidden=False)],
    )
    if not providers:
        raise RuntimeError("No configured providers found for random strategy")
    pid = random.choice(providers)
    cfg = d._configs.get(pid, {})
    return pid, cfg.get("default_model")


def goblin_provider() -> tuple[None, None]:
    """
    Goblin's auto-routing mode.

    Returns (None, None) to let the dispatcher run its full selection
    pipeline: hybrid scoring, context window filtering, health checks,
    fallback chains.
    """
    return None, None


STRATEGIES = {
    "goblin": goblin_provider,
    "cheapest": cheapest_provider,
    "strongest": strongest_provider,
    "random": random_provider,
}
