"""
Citation graph tool for Goblin Assistant.

Given a paper (arXiv ID, DOI, or title), builds a graph of citation relationships
using the Semantic Scholar Graph API (free, no key required, 100 req/5 min).

Output: nodes (papers) + edges (citation links) in a structure the LLM can narrate.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from ..registry import ToolDefinition, ToolParameter, register_tool

_SS_BASE = "https://api.semanticscholar.org/graph/v1"
_PAPER_FIELDS = "title,authors,year,url,externalIds"
_MAX_LIMIT = 25
_MAX_DEPTH = 2
_MAX_TOTAL_NODES = 50

# arXiv ID: NNNN.NNNNN or NNNN.NNNNNN (old format: archive/NNNNNNN)
_ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}$")
# DOI: starts with 10. followed by at least 4 digits and a slash
_DOI_RE = re.compile(r"^10\.\d{4,}/")
# Semantic Scholar native ID: 40-char hex
_SS_ID_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# ID resolution
# ---------------------------------------------------------------------------


def _classify_id(raw: str) -> tuple[str, str]:
    """
    Return (ss_paper_id, kind) where kind is 'direct' or 'search'.
    'direct' means the ID can be passed straight to /paper/{id}.
    'search' means we need to query /paper/search first.
    """
    raw = raw.strip()
    if _SS_ID_RE.match(raw):
        return raw, "direct"
    if raw.upper().startswith("ARXIV:"):
        return raw, "direct"
    if raw.upper().startswith("DOI:"):
        return raw, "direct"
    if _ARXIV_RE.match(raw):
        return f"ARXIV:{raw}", "direct"
    if _DOI_RE.match(raw):
        return f"DOI:{raw}", "direct"
    return raw, "search"


async def _resolve_paper_id(raw: str, client: httpx.AsyncClient) -> Optional[str]:
    """Resolve raw input to a Semantic Scholar paperId, or None on failure."""
    ss_id, kind = _classify_id(raw)
    if kind == "direct":
        return ss_id

    # Title search
    try:
        resp = await client.get(
            f"{_SS_BASE}/paper/search",
            params={"query": ss_id, "limit": 1, "fields": "paperId,title"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:  # noqa: BLE001
        return None

    papers = data.get("data", [])
    if not papers:
        return None
    return papers[0].get("paperId")


# ---------------------------------------------------------------------------
# Paper / neighbor fetching
# ---------------------------------------------------------------------------


def _normalize_node(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a consistent node dict from a Semantic Scholar paper object."""
    authors = [a.get("name", "") for a in raw.get("authors") or []]
    url = raw.get("url") or ""
    if not url:
        pid = raw.get("paperId", "")
        url = f"https://www.semanticscholar.org/paper/{pid}" if pid else ""
    return {
        "id": raw.get("paperId", ""),
        "title": raw.get("title") or "",
        "authors": authors,
        "year": raw.get("year"),
        "url": url,
    }


async def _fetch_paper(paper_id: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """Fetch a single paper's metadata. Returns normalized node or None."""
    try:
        resp = await client.get(
            f"{_SS_BASE}/paper/{quote(paper_id, safe=':')}",
            params={"fields": _PAPER_FIELDS},
        )
        resp.raise_for_status()
        return _normalize_node(resp.json())
    except Exception:  # noqa: BLE001
        return None


async def _fetch_neighbors(
    paper_id: str,
    direction: str,
    limit: int,
    client: httpx.AsyncClient,
) -> List[Dict[str, Any]]:
    """
    Fetch citation neighbors for a paper.
    direction: "citations" or "references"
    Returns list of (neighbor_paper_node, edge) tuples packed as dicts.
    """
    endpoint = f"{_SS_BASE}/paper/{quote(paper_id, safe=':')}/{direction}"
    neighbor_field = "citingPaper" if direction == "citations" else "citedPaper"
    fields = f"{neighbor_field}.{_PAPER_FIELDS.replace(',', f',{neighbor_field}.')}"

    try:
        resp = await client.get(
            endpoint,
            params={"fields": fields, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:  # noqa: BLE001
        return []

    results = []
    for item in data.get("data", []):
        raw = item.get(neighbor_field)
        if not raw or not raw.get("paperId"):
            continue
        node = _normalize_node(raw)
        if direction == "citations":
            # neighbor cites the root
            edge = {"source": node["id"], "target": paper_id, "relation": "cites"}
        else:
            # root cites the neighbor
            edge = {"source": paper_id, "target": node["id"], "relation": "cites"}
        results.append({"node": node, "edge": edge})
    return results


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


async def _handle_citation_graph(
    paper_id: str,
    direction: str = "both",
    depth: int = 1,
    limit: int = 10,
) -> Dict[str, Any]:
    depth = max(1, min(depth, _MAX_DEPTH))
    limit = max(1, min(limit, _MAX_LIMIT))
    directions = ["references", "citations"] if direction == "both" else [direction]

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Resolve input to a Semantic Scholar paper ID
        resolved_id = await _resolve_paper_id(paper_id, client)
        if not resolved_id:
            return {"error": f"Could not find a paper matching: {paper_id!r}"}

        # Fetch root paper metadata
        root = await _fetch_paper(resolved_id, client)
        if not root:
            return {"error": f"Could not fetch paper metadata for ID: {resolved_id}"}

        nodes: Dict[str, Dict[str, Any]] = {root["id"]: root}
        edges: List[Dict[str, Any]] = []

        # BFS queue: (paper_id, current_depth)
        queue = [(resolved_id, 1)]
        visited = {resolved_id}

        while queue:
            current_id, current_depth = queue.pop(0)

            # Secondary hops use a smaller per-direction limit to stay within rate limits
            hop_limit = limit if current_depth == 1 else min(limit, 5)

            for dir_ in directions:
                pairs = await _fetch_neighbors(current_id, dir_, hop_limit, client)
                for pair in pairs:
                    node = pair["node"]
                    nid = node["id"]
                    if nid and nid not in nodes:
                        nodes[nid] = node
                    if pair["edge"] not in edges:
                        edges.append(pair["edge"])

                    if (
                        current_depth < depth
                        and nid
                        and nid not in visited
                        and len(nodes) < _MAX_TOTAL_NODES
                    ):
                        visited.add(nid)
                        queue.append((nid, current_depth + 1))

    all_nodes = [v for k, v in nodes.items() if k != root["id"]]

    return {
        "root": root,
        "nodes": all_nodes,
        "edges": edges,
        "direction": direction,
        "depth": depth,
        "total_nodes": len(all_nodes),
        "total_edges": len(edges),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_tool(
    ToolDefinition(
        name="citation_graph",
        description=(
            "Build a citation graph for an academic paper — showing what it cites "
            "(references) and/or what cites it (forward citations). Use when the user "
            "wants to explore a paper's intellectual lineage, find related work, or "
            "understand a paper's impact. Accepts an arXiv ID (e.g. '2301.00001'), "
            "a DOI (e.g. '10.1145/12345'), or a paper title."
        ),
        parameters=[
            ToolParameter(
                name="paper_id",
                type="string",
                description=(
                    "The paper to look up. Can be an arXiv ID (e.g. '1706.03762'), "
                    "a DOI (e.g. '10.1145/3034786'), or a paper title."
                ),
            ),
            ToolParameter(
                name="direction",
                type="string",
                description=(
                    "Which edges to fetch: 'references' (papers this paper cites), "
                    "'citations' (papers that cite this paper), or 'both'."
                ),
                required=False,
                enum=["references", "citations", "both"],
                default="both",
            ),
            ToolParameter(
                name="depth",
                type="integer",
                description=(
                    "Graph traversal depth: 1 returns direct neighbors only; "
                    "2 also fetches neighbors-of-neighbors (more API calls)."
                ),
                required=False,
                default=1,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Max papers to fetch per node per direction (1–25). Defaults to 10.",
                required=False,
                default=10,
            ),
        ],
        handler=_handle_citation_graph,
        category="academic",
    )
)
