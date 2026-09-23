"""Tests for the web_search assistant tool."""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DDG_RAW = [
    {"title": "Result A", "href": "https://example.com/a", "body": "Snippet A"},
    {"title": "Result B", "href": "https://example.com/b", "body": "Snippet B"},
]

_BRAVE_RAW = {
    "web": {
        "results": [
            {
                "title": "Brave Result",
                "url": "https://brave.com/result",
                "description": "Brave snippet",
            }
        ]
    }
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_brave_search_success():
    """Brave Search is used when key is present and returns results."""
    with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "test-key"}):
        with patch(
            "api.assistant_tools.skills.web_search.get_json",
            return_value=_BRAVE_RAW,
        ):
            from api.assistant_tools.skills.web_search import _handle_web_search

            result = await _handle_web_search("test query", max_results=3)

    assert result["provider"] == "brave"
    assert result["query"] == "test query"
    assert len(result["results"]) == 1
    assert result["results"][0]["url"] == "https://brave.com/result"


@pytest.mark.asyncio
async def test_brave_search_fallback_to_ddg():
    """Falls back to DuckDuckGo when Brave returns an error."""
    def _fake_ddg_sync(query: str, max_results: int):
        return {
            "results": [{"title": "DDG", "url": "https://ddg.com", "snippet": "s"}],
            "query": query,
            "provider": "duckduckgo",
            "count": 1,
        }

    with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "test-key"}):
        with patch(
            "api.assistant_tools.skills.web_search.get_json",
            side_effect=RuntimeError("HTTP 500"),
        ):
            with patch(
                "api.assistant_tools.skills.web_search._ddg_search_sync",
                side_effect=_fake_ddg_sync,
            ):
                from api.assistant_tools.skills.web_search import _handle_web_search

                result = await _handle_web_search("fallback query")

    assert result["provider"] == "duckduckgo"
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_ddg_search_no_key():
    """Uses DuckDuckGo directly when BRAVE_SEARCH_API_KEY is not set."""

    def _fake_ddg_sync(query: str, max_results: int):
        return {
            "results": [
                {"title": t["title"], "url": t["href"], "snippet": t["body"]} for t in _DDG_RAW
            ],
            "query": query,
            "provider": "duckduckgo",
            "count": len(_DDG_RAW),
        }

    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("BRAVE_SEARCH_API_KEY", None)

        with patch(
            "api.assistant_tools.skills.web_search._ddg_search_sync",
            side_effect=_fake_ddg_sync,
        ):
            from api.assistant_tools.skills.web_search import _handle_web_search

            result = await _handle_web_search("no key query", max_results=2)

    assert result["provider"] == "duckduckgo"
    assert result["count"] == 2
    assert result["results"][0]["url"] == "https://example.com/a"


@pytest.mark.asyncio
async def test_max_results_capped():
    """max_results is capped at 10 even if caller passes a higher value."""
    call_args: dict = {}

    def _fake_ddg_sync(query: str, max_results: int):
        call_args["max_results"] = max_results
        return {"results": [], "query": query, "provider": "duckduckgo", "count": 0}

    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("BRAVE_SEARCH_API_KEY", None)

        with patch(
            "api.assistant_tools.skills.web_search._ddg_search_sync",
            side_effect=_fake_ddg_sync,
        ):
            from api.assistant_tools.skills.web_search import _handle_web_search

            await _handle_web_search("cap test", max_results=99)

    assert call_args["max_results"] <= 10
