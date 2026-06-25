"""
Web search tool for Goblin Assistant.

Registers a web_search tool with a cost-optimized two-tier fallback:
  1. Brave Search API (if BRAVE_SEARCH_API_KEY is set) — free tier 2k req/month
  2. DuckDuckGo via duckduckgo-search (always free, no key needed)
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

import httpx

from ..registry import ToolDefinition, ToolParameter, register_tool

_BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_MAX_RESULTS_CAP = 10


# ---------------------------------------------------------------------------
# Brave Search
# ---------------------------------------------------------------------------


async def _brave_search(query: str, max_results: int) -> Dict[str, Any]:
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": min(max_results, _MAX_RESULTS_CAP)}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_BRAVE_ENDPOINT, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Brave Search request failed: {exc}"}

    raw_results: List[Dict] = data.get("web", {}).get("results", [])
    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", ""),
        }
        for r in raw_results
    ]
    return {
        "results": results,
        "query": query,
        "provider": "brave",
        "count": len(results),
    }


# ---------------------------------------------------------------------------
# DuckDuckGo (free fallback)
# ---------------------------------------------------------------------------


def _ddg_search_sync(query: str, max_results: int) -> Dict[str, Any]:
    try:
        from duckduckgo_search import DDGS  # type: ignore[import]
    except ImportError:
        return {"error": "duckduckgo-search is not installed"}

    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=min(max_results, _MAX_RESULTS_CAP)))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"DuckDuckGo search failed: {exc}"}

    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in raw
    ]
    return {
        "results": results,
        "query": query,
        "provider": "duckduckgo",
        "count": len(results),
    }


async def _ddg_search(query: str, max_results: int) -> Dict[str, Any]:
    return await asyncio.to_thread(_ddg_search_sync, query, max_results)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


async def _handle_web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    max_results = max(1, min(max_results, _MAX_RESULTS_CAP))

    if os.environ.get("BRAVE_SEARCH_API_KEY"):
        result = await _brave_search(query, max_results)
        if "error" not in result:
            return result

    return await _ddg_search(query, max_results)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_tool(
    ToolDefinition(
        name="web_search",
        description=(
            "Use when the user asks about current events, breaking news, live "
            "prices, recent announcements, or any factual question that requires "
            "up-to-date internet information not available in the model's training "
            "data. Returns titles, URLs, and snippets from web search results."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The search query to send to the web search engine.",
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Number of results to return (1–10). Defaults to 5.",
                required=False,
                default=5,
            ),
        ],
        handler=_handle_web_search,
        category="web",
    )
)
