"""Tests for the academic_search assistant tool."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ARXIV_ATOM_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Attention Is All You Need</title>
    <summary>We propose a new model architecture based solely on attention mechanisms.</summary>
    <published>2023-01-01T00:00:00Z</published>
    <author><name>Alice Researcher</name></author>
    <author><name>Bob Scientist</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00002v1</id>
    <title>BERT: Pre-training of Deep Bidirectional Transformers</title>
    <summary>We introduce BERT, designed to pre-train deep bidirectional representations.</summary>
    <published>2023-01-02T00:00:00Z</published>
    <author><name>Carol Engineer</name></author>
  </entry>
</feed>
"""

_SEMANTIC_SCHOLAR_JSON = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Deep Learning",
            "abstract": "A comprehensive survey of deep learning methods.",
            "year": 2024,
            "authors": [{"name": "Yann LeCun"}, {"name": "Geoffrey Hinton"}],
            "url": "https://www.semanticscholar.org/paper/abc123",
        }
    ]
}


def _make_httpx_response(data: Any, status_code: int = 200, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _mock_async_client(mock_resp: MagicMock):
    """Return a patch context for httpx.AsyncClient that returns mock_resp on .get()."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_client


# ---------------------------------------------------------------------------
# arXiv tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arxiv_search_success():
    """arXiv returns parsed results with title, authors, abstract, url, published."""
    mock_resp = _make_httpx_response({}, text=_ARXIV_ATOM_XML)

    ctx, mock_client = _mock_async_client(mock_resp)

    with patch(
        "api.assistant_tools.skills.academic_search.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.academic_search import _handle_academic_search

        result = await _handle_academic_search("transformer", source="arxiv", max_results=5)

    assert result["provider"] == "arxiv"
    assert result["query"] == "transformer"
    assert result["count"] == 2
    first = result["results"][0]
    assert first["title"] == "Attention Is All You Need"
    assert "Alice Researcher" in first["authors"]
    assert first["published"] == "2023-01"
    assert "arxiv.org/abs" in first["url"]
    assert first["source"] == "arxiv"


@pytest.mark.asyncio
async def test_arxiv_category_filter_sent_in_query():
    """arXiv category is included in search_query param when provided."""
    mock_resp = _make_httpx_response({}, text="<feed xmlns='http://www.w3.org/2005/Atom'></feed>")

    ctx, mock_client = _mock_async_client(mock_resp)

    with patch(
        "api.assistant_tools.skills.academic_search.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.academic_search import _handle_academic_search

        await _handle_academic_search("reinforcement learning", source="arxiv", category="cs.AI")

    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"] if call_kwargs[1] else call_kwargs[0][1]
    assert "cat:cs.AI" in params["search_query"]


@pytest.mark.asyncio
async def test_arxiv_http_error_returns_error_dict():
    """arXiv HTTP failure returns an error dict without raising."""
    mock_resp = _make_httpx_response({}, status_code=503, text="")

    ctx, _ = _mock_async_client(mock_resp)

    with patch(
        "api.assistant_tools.skills.academic_search.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.academic_search import _handle_academic_search

        result = await _handle_academic_search("test", source="arxiv")

    assert "error" in result


# ---------------------------------------------------------------------------
# Semantic Scholar tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_scholar_search_success():
    """Semantic Scholar returns parsed results from JSON response."""
    mock_resp = _make_httpx_response(_SEMANTIC_SCHOLAR_JSON)

    ctx, _ = _mock_async_client(mock_resp)

    with patch(
        "api.assistant_tools.skills.academic_search.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.academic_search import _handle_academic_search

        result = await _handle_academic_search("deep learning", source="semantic_scholar")

    assert result["provider"] == "semantic_scholar"
    assert result["count"] == 1
    paper = result["results"][0]
    assert paper["title"] == "Deep Learning"
    assert "Yann LeCun" in paper["authors"]
    assert paper["published"] == "2024"
    assert paper["source"] == "semantic_scholar"


@pytest.mark.asyncio
async def test_semantic_scholar_http_error_returns_error_dict():
    """Semantic Scholar HTTP failure returns an error dict without raising."""
    mock_resp = _make_httpx_response({}, status_code=429)

    ctx, _ = _mock_async_client(mock_resp)

    with patch(
        "api.assistant_tools.skills.academic_search.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.academic_search import _handle_academic_search

        result = await _handle_academic_search("test", source="semantic_scholar")

    assert "error" in result


# ---------------------------------------------------------------------------
# max_results capping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_results_capped_at_10():
    """max_results > 10 is silently capped at 10 before the API call."""
    mock_resp = _make_httpx_response({}, text="<feed xmlns='http://www.w3.org/2005/Atom'></feed>")

    ctx, mock_client = _mock_async_client(mock_resp)

    with patch(
        "api.assistant_tools.skills.academic_search.httpx.AsyncClient",
        return_value=ctx,
    ):
        from api.assistant_tools.skills.academic_search import _handle_academic_search

        await _handle_academic_search("quantum computing", source="arxiv", max_results=99)

    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"] if call_kwargs[1] else call_kwargs[0][1]
    assert params["max_results"] <= 10


# ---------------------------------------------------------------------------
# Registry smoke test
# ---------------------------------------------------------------------------


def test_academic_search_registered():
    """academic_search tool is present in the global tool registry."""
    import api.assistant_tools  # noqa: F401 — triggers registration
    from api.assistant_tools.registry import TOOL_REGISTRY

    assert "academic_search" in TOOL_REGISTRY
    defn = TOOL_REGISTRY["academic_search"]
    assert defn.category == "academic"
    param_names = {p.name for p in defn.parameters}
    assert {"query", "source", "max_results", "category"} == param_names
