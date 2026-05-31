"""Tests for the citation_graph assistant tool."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_ROOT_PAPER = {
    "paperId": "abc123def456abc123def456abc123def456abc1",
    "title": "Attention Is All You Need",
    "authors": [{"name": "Vaswani et al."}],
    "year": 2017,
    "url": "https://www.semanticscholar.org/paper/abc123def456abc123def456abc123def456abc1",
    "externalIds": {"ArXiv": "1706.03762"},
}

_CITING_PAPER = {
    "paperId": "cccccccccccccccccccccccccccccccccccccccc",
    "title": "BERT: Pre-training of Deep Bidirectional Transformers",
    "authors": [{"name": "Devlin et al."}],
    "year": 2018,
    "url": "https://www.semanticscholar.org/paper/cccccccc",
    "externalIds": {},
}

_CITED_PAPER = {
    "paperId": "dddddddddddddddddddddddddddddddddddddddd",
    "title": "Neural Machine Translation by Jointly Learning to Align and Translate",
    "authors": [{"name": "Bahdanau et al."}],
    "year": 2014,
    "url": "https://www.semanticscholar.org/paper/dddddddd",
    "externalIds": {},
}


def _make_httpx_response(data: Any, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _citations_response(citing_paper: dict) -> dict:
    """Simulate /citations response (papers that cite the root)."""
    return {"data": [{"citingPaper": citing_paper}]}


def _references_response(cited_paper: dict) -> dict:
    """Simulate /references response (papers the root cites)."""
    return {"data": [{"citedPaper": cited_paper}]}


# ---------------------------------------------------------------------------
# ID classification tests (no HTTP calls needed)
# ---------------------------------------------------------------------------


def test_resolve_arxiv_id_format():
    """Pure arXiv IDs are classified as direct without a search call."""
    from api.assistant_tools.skills.citation_graph import _classify_id

    ss_id, kind = _classify_id("1706.03762")
    assert kind == "direct"
    assert ss_id == "ARXIV:1706.03762"


def test_resolve_doi_format():
    """DOI strings are classified as direct without a search call."""
    from api.assistant_tools.skills.citation_graph import _classify_id

    ss_id, kind = _classify_id("10.1145/3034786")
    assert kind == "direct"
    assert ss_id == "DOI:10.1145/3034786"


def test_resolve_explicit_arxiv_prefix():
    """Explicit ARXIV: prefix is passed through as direct."""
    from api.assistant_tools.skills.citation_graph import _classify_id

    ss_id, kind = _classify_id("ARXIV:1706.03762")
    assert kind == "direct"
    assert "ARXIV" in ss_id


def test_resolve_ss_hex_id():
    """40-char hex Semantic Scholar IDs are direct."""
    from api.assistant_tools.skills.citation_graph import _classify_id

    raw = "abc123def456abc123def456abc123def456abc1"
    ss_id, kind = _classify_id(raw)
    assert kind == "direct"
    assert ss_id == raw


def test_resolve_title_search():
    """Free-text titles are classified as search."""
    from api.assistant_tools.skills.citation_graph import _classify_id

    _, kind = _classify_id("Attention Is All You Need")
    assert kind == "search"


# ---------------------------------------------------------------------------
# Handler integration tests (mocked HTTP)
# ---------------------------------------------------------------------------


def _build_client_mock(responses: list[Any]) -> tuple[MagicMock, AsyncMock]:
    """
    Build an AsyncClient mock that returns `responses` in order on each .get() call.
    Returns (ctx_manager_mock, async_client_mock).
    """
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[_make_httpx_response(r) for r in responses])

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


@pytest.mark.asyncio
async def test_citation_graph_references_only():
    """direction='references' fetches /references and returns cites edges with root as source."""
    # Calls in order: _fetch_paper(root), _fetch_neighbors(root, references)
    responses = [
        _ROOT_PAPER,
        _references_response(_CITED_PAPER),
    ]
    ctx, _ = _build_client_mock(responses)

    with patch(
        "api.assistant_tools.skills.citation_graph.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.citation_graph import _handle_citation_graph

        result = await _handle_citation_graph(
            "abc123def456abc123def456abc123def456abc1",
            direction="references",
            depth=1,
        )

    assert result["root"]["title"] == "Attention Is All You Need"
    assert result["total_nodes"] == 1
    assert result["total_edges"] == 1
    edge = result["edges"][0]
    assert edge["source"] == _ROOT_PAPER["paperId"]
    assert edge["target"] == _CITED_PAPER["paperId"]
    assert edge["relation"] == "cites"


@pytest.mark.asyncio
async def test_citation_graph_citations_only():
    """direction='citations' fetches /citations and returns edges with neighbor as source."""
    responses = [
        _ROOT_PAPER,
        _citations_response(_CITING_PAPER),
    ]
    ctx, _ = _build_client_mock(responses)

    with patch(
        "api.assistant_tools.skills.citation_graph.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.citation_graph import _handle_citation_graph

        result = await _handle_citation_graph(
            "abc123def456abc123def456abc123def456abc1",
            direction="citations",
            depth=1,
        )

    assert result["total_edges"] == 1
    edge = result["edges"][0]
    assert edge["source"] == _CITING_PAPER["paperId"]
    assert edge["target"] == _ROOT_PAPER["paperId"]


@pytest.mark.asyncio
async def test_citation_graph_both_directions():
    """direction='both' fetches both /references and /citations."""
    responses = [
        _ROOT_PAPER,
        _references_response(_CITED_PAPER),
        _citations_response(_CITING_PAPER),
    ]
    ctx, _ = _build_client_mock(responses)

    with patch(
        "api.assistant_tools.skills.citation_graph.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.citation_graph import _handle_citation_graph

        result = await _handle_citation_graph(
            "abc123def456abc123def456abc123def456abc1",
            direction="both",
            depth=1,
        )

    assert result["total_nodes"] == 2
    assert result["total_edges"] == 2


@pytest.mark.asyncio
async def test_citation_graph_depth2_fetches_secondary_neighbors():
    """depth=2 triggers neighbor fetches for secondary nodes."""
    secondary_paper = {
        "paperId": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        "title": "Secondary Paper",
        "authors": [],
        "year": 2020,
        "url": "",
        "externalIds": {},
    }

    responses = [
        _ROOT_PAPER,                                  # _fetch_paper(root)
        _references_response(_CITED_PAPER),           # depth-1 references
        _citations_response(_CITING_PAPER),           # depth-1 citations
        _references_response(secondary_paper),        # depth-2 refs for cited paper
        _citations_response({"paperId": "", "title": "", "authors": [], "year": None, "url": "", "externalIds": {}}),  # depth-2 cits for citing paper (empty paperId → skipped)
    ]
    ctx, mock_client = _build_client_mock(responses)

    with patch(
        "api.assistant_tools.skills.citation_graph.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.citation_graph import _handle_citation_graph

        result = await _handle_citation_graph(
            "abc123def456abc123def456abc123def456abc1",
            direction="both",
            depth=2,
            limit=5,
        )

    # At least 3 nodes expected: cited, citing, secondary
    assert result["total_nodes"] >= 2
    assert result["depth"] == 2


@pytest.mark.asyncio
async def test_root_paper_not_found():
    """Returns an error dict when the paper lookup fails."""
    ctx, _ = _build_client_mock([{"error": "not found"}])

    with patch(
        "api.assistant_tools.skills.citation_graph.httpx.AsyncClient",
        return_value=ctx,
    ):
        # Patch _fetch_paper to return None so we hit the error branch
        with patch(
            "api.assistant_tools.skills.citation_graph._fetch_paper",
            return_value=None,
        ):
            from api.assistant_tools.skills.citation_graph import _handle_citation_graph

            result = await _handle_citation_graph(
                "abc123def456abc123def456abc123def456abc1",
            )

    assert "error" in result


@pytest.mark.asyncio
async def test_title_search_resolves_paper_id():
    """Free-text title triggers /paper/search, then proceeds normally."""
    search_resp = {"data": [{"paperId": _ROOT_PAPER["paperId"], "title": _ROOT_PAPER["title"]}]}

    responses = [
        search_resp,                          # _resolve_paper_id title search
        _ROOT_PAPER,                          # _fetch_paper(resolved)
        _references_response(_CITED_PAPER),   # references
        _citations_response(_CITING_PAPER),   # citations
    ]
    ctx, _ = _build_client_mock(responses)

    with patch(
        "api.assistant_tools.skills.citation_graph.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.citation_graph import _handle_citation_graph

        result = await _handle_citation_graph("Attention Is All You Need", direction="both")

    assert result["root"]["title"] == "Attention Is All You Need"
    assert "error" not in result


@pytest.mark.asyncio
async def test_limit_capped_at_25():
    """limit > 25 is silently capped at 25."""
    responses = [
        _ROOT_PAPER,
        _references_response(_CITED_PAPER),
    ]
    ctx, mock_client = _build_client_mock(responses)

    with patch(
        "api.assistant_tools.skills.citation_graph.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.citation_graph import _handle_citation_graph

        await _handle_citation_graph(
            "abc123def456abc123def456abc123def456abc1",
            direction="references",
            limit=999,
        )

    # The /references call should have limit <= 25
    refs_call = mock_client.get.call_args_list[1]
    params = refs_call[1].get("params") or refs_call[0][1]
    assert params["limit"] <= 25


# ---------------------------------------------------------------------------
# Registry smoke test
# ---------------------------------------------------------------------------


def test_citation_graph_registered():
    """citation_graph tool is present in TOOL_REGISTRY with correct shape."""
    import api.assistant_tools  # noqa: F401 — triggers registration
    from api.assistant_tools.registry import TOOL_REGISTRY

    assert "citation_graph" in TOOL_REGISTRY
    defn = TOOL_REGISTRY["citation_graph"]
    assert defn.category == "academic"
    param_names = {p.name for p in defn.parameters}
    assert {"paper_id", "direction", "depth", "limit"} == param_names
    direction_param = next(p for p in defn.parameters if p.name == "direction")
    assert set(direction_param.enum) == {"references", "citations", "both"}
