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


def cheapest_provider() -> tuple[str, Optional[str]]:
    """Return the first provider in cheapest-cost order."""
    d = _dispatcher()
    order = d._cheapest_order()
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
    top = d.top_providers_for("reasoning", prefer_cost=False, limit=1)
    if top:
        pid = top[0]
        cfg = d._configs.get(pid, {})
        return pid, cfg.get("default_model")
    # Fallback: pick the first in hybrid order (quality-aware)
    order = d._hybrid_order()
    if not order:
        raise RuntimeError("No configured providers found for strongest strategy")
    pid = order[0]
    cfg = d._configs.get(pid, {})
    return pid, cfg.get("default_model")


def random_provider() -> tuple[str, Optional[str]]:
    """Return a randomly chosen configured provider."""
    d = _dispatcher()
    providers = [
        p for p in d.list_providers(include_hidden=False) if d.is_configured(p["id"])
    ]
    if not providers:
        raise RuntimeError("No configured providers found for random strategy")
    item = random.choice(providers)
    return item["id"], item.get("default_model")


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
