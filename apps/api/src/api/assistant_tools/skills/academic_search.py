"""
Academic search tool for Goblin Assistant.

Searches scholarly databases for papers and research articles using free APIs:
  1. arXiv (default) — preprints in CS, physics, math, econ, bio; no key required
  2. Semantic Scholar — broad multi-discipline index; no key required (100 req/5 min)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx

from ..registry import ToolDefinition, ToolParameter, register_tool

_MAX_RESULTS_CAP = 10
_ARXIV_ENDPOINT = "http://export.arxiv.org/api/query"
_SEMANTIC_SCHOLAR_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"

_ATOM_NS = "http://www.w3.org/2005/Atom"


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------


async def _search_arxiv(query: str, max_results: int, category: Optional[str]) -> Dict[str, Any]:
    search_query = f"all:{quote_plus(query)}"
    if category:
        search_query = f"cat:{category} AND {search_query}"

    params = {
        "search_query": search_query,
        "max_results": max_results,
        "sortBy": "relevance",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_ARXIV_ENDPOINT, params=params)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as exc:  # noqa: BLE001
        return {"error": f"arXiv request failed: {exc}"}

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return {"error": f"arXiv XML parse error: {exc}"}

    results: List[Dict[str, Any]] = []
    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        title_el = entry.find(f"{{{_ATOM_NS}}}title")
        summary_el = entry.find(f"{{{_ATOM_NS}}}summary")
        published_el = entry.find(f"{{{_ATOM_NS}}}published")
        id_el = entry.find(f"{{{_ATOM_NS}}}id")

        authors = [
            a.find(f"{{{_ATOM_NS}}}name").text or ""
            for a in entry.findall(f"{{{_ATOM_NS}}}author")
            if a.find(f"{{{_ATOM_NS}}}name") is not None
        ]

        arxiv_id = (id_el.text or "").strip() if id_el is not None else ""
        # Normalise to canonical abs URL
        url = arxiv_id if arxiv_id.startswith("http") else f"https://arxiv.org/abs/{arxiv_id}"

        published_raw = (published_el.text or "").strip() if published_el is not None else ""
        published = published_raw[:7] if published_raw else ""  # "YYYY-MM"

        results.append(
            {
                "title": (title_el.text or "").strip() if title_el is not None else "",
                "authors": authors,
                "abstract": (summary_el.text or "").strip() if summary_el is not None else "",
                "url": url,
                "published": published,
                "source": "arxiv",
            }
        )

    return {
        "results": results,
        "query": query,
        "provider": "arxiv",
        "count": len(results),
    }


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------


async def _search_semantic_scholar(query: str, max_results: int) -> Dict[str, Any]:
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,authors,abstract,year,url,externalIds",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_SEMANTIC_SCHOLAR_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Semantic Scholar request failed: {exc}"}

    raw: List[Dict] = data.get("data", [])
    results = []
    for paper in raw:
        authors = [a.get("name", "") for a in paper.get("authors", [])]
        url = paper.get("url") or ""
        if not url:
            paper_id = paper.get("paperId", "")
            url = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""

        year = paper.get("year")
        published = str(year) if year else ""

        results.append(
            {
                "title": paper.get("title") or "",
                "authors": authors,
                "abstract": paper.get("abstract") or "",
                "url": url,
                "published": published,
                "source": "semantic_scholar",
            }
        )

    return {
        "results": results,
        "query": query,
        "provider": "semantic_scholar",
        "count": len(results),
    }


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


async def _handle_academic_search(
    query: str,
    source: str = "arxiv",
    max_results: int = 5,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    max_results = max(1, min(max_results, _MAX_RESULTS_CAP))

    if source == "semantic_scholar":
        return await _search_semantic_scholar(query, max_results)

    return await _search_arxiv(query, max_results, category)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_tool(
    ToolDefinition(
        name="academic_search",
        description=(
            "Search academic papers and research articles from arXiv or Semantic Scholar. "
            "Use when the user asks for research papers, academic literature, scientific "
            "studies, preprints, or citations on a topic. Returns titles, authors, "
            "abstracts, publication dates, and URLs."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Search query or research topic.",
            ),
            ToolParameter(
                name="source",
                type="string",
                description=(
                    "Database to search. 'arxiv' (default) covers CS, physics, math, "
                    "economics, and biology preprints. 'semantic_scholar' covers a broader "
                    "multi-discipline index of published papers."
                ),
                required=False,
                enum=["arxiv", "semantic_scholar"],
                default="arxiv",
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Number of results to return (1–10). Defaults to 5.",
                required=False,
                default=5,
            ),
            ToolParameter(
                name="category",
                type="string",
                description=(
                    "arXiv subject category filter (only applies when source='arxiv'). "
                    "Examples: 'cs.AI', 'cs.LG', 'q-fin.TR', 'math.CO', 'physics.optics'."
                ),
                required=False,
                default=None,
            ),
        ],
        handler=_handle_academic_search,
        category="academic",
    )
)
