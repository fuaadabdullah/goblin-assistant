"""
Memory benchmark probe.

Runs retrieval queries against the seeded benchmark user and returns
raw retrieval results for the scorer to evaluate.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Tuple


async def probe_query(
    query_text: str,
    user_id: str,
    *,
    limit: int = 10,
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Run one retrieval query and return (results, latency_ms).

    Results are raw dicts from the retrieval service, each containing
    at minimum: 'id', 'fact_text' (or 'content'), 'score'.
    """
    from api.services.memory_core import memory_core_service  # noqa: PLC0415

    t0 = time.perf_counter()
    try:
        results = await memory_core_service.retrieve_memory_context(
            user_id=user_id,
            query=query_text,
            limit=limit,
        )
    except Exception:
        results = []
    latency_ms = (time.perf_counter() - t0) * 1000

    # Normalise: ensure each result has both 'id' and 'fact_text'
    normalised = []
    for item in results or []:
        if isinstance(item, dict):
            fact_text = (
                item.get("fact_text") or item.get("content") or item.get("text") or ""
            )
            normalised.append({**item, "fact_text": fact_text})
    return normalised, latency_ms


async def probe_scenario(
    scenario: Dict[str, Any],
    user_id: str,
    *,
    retrieval_limit: int = 10,
    verbose: bool = False,
) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]], float]]:
    """
    Probe all queries in a scenario.

    Returns a list of (query_dict, results, latency_ms) tuples.
    """
    output = []
    for query in scenario.get("queries", []):
        results, latency_ms = await probe_query(
            query["text"],
            user_id,
            limit=retrieval_limit,
        )
        output.append((query, results, latency_ms))
        if verbose:
            hits = len(results)
            print(
                f"    [{query['query_id']}] {query['text'][:60]} "
                f"→ {hits} results  ({latency_ms:.0f} ms)"
            )
        # Small delay between queries to avoid rate-limiting the embedding service
        await asyncio.sleep(0.1)
    return output
