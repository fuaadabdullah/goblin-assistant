"""Runtime tests for api.search_router."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.search_router import COLLECTIONS, router, simple_text_search


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def setup_function() -> None:
    COLLECTIONS.clear()


def test_add_and_get_collection_documents() -> None:
    client = _client()

    add_resp = client.post(
        "/search/collections/docs/add",
        params={"document": "hello world", "id": "doc-1"},
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["document_id"] == "doc-1"

    get_resp = client.get("/search/collections/docs/documents")
    assert get_resp.status_code == 200
    docs = get_resp.json()["documents"]
    assert len(docs) == 1
    assert docs[0]["document"] == "hello world"


def test_list_collections_reflects_added_documents() -> None:
    client = _client()

    client.post(
        "/search/collections/alpha/add",
        params={"document": "first"},
    )
    client.post(
        "/search/collections/beta/add",
        params={"document": "second"},
    )

    resp = client.get("/search/collections")
    assert resp.status_code == 200
    assert set(resp.json()["collections"]) == {"alpha", "beta"}


def test_query_returns_empty_when_collection_has_no_documents() -> None:
    client = _client()

    resp = client.post(
        "/search/query",
        json={"query": "python", "collection_name": "docs"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []
    assert body["total_results"] == 0


def test_query_returns_ranked_and_limited_results() -> None:
    client = _client()

    client.post(
        "/search/collections/docs/add",
        params={"document": "python fastapi basics", "id": "one"},
    )
    client.post(
        "/search/collections/docs/add",
        params={"document": "python python tips", "id": "two"},
    )
    client.post(
        "/search/collections/docs/add",
        params={"document": "javascript guide", "id": "three"},
    )

    resp = client.post(
        "/search/query",
        json={
            "query": "python",
            "collection_name": "docs",
            "n_results": 2,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_results"] == 2
    assert len(body["results"]) == 2
    assert all("python" in r["document"].lower() for r in body["results"])


def test_query_returns_500_when_search_raises() -> None:
    client = _client()

    client.post(
        "/search/collections/docs/add",
        params={"document": "will trigger path"},
    )

    with patch(
        "api.search_router.simple_text_search",
        side_effect=RuntimeError("boom"),
    ):
        resp = client.post(
            "/search/query",
            json={"query": "test", "collection_name": "docs"},
        )

    assert resp.status_code == 500
    assert "Search failed" in resp.json()["detail"]


def test_simple_text_search_prefers_exact_phrase() -> None:
    docs = [
        {"id": "a", "document": "python async testing"},
        {"id": "b", "document": "python testing tips"},
    ]

    results = simple_text_search("python async", docs, n_results=2)

    assert len(results) == 2
    assert results[0]["id"] == "a"


def test_simple_text_search_returns_empty_on_no_match() -> None:
    docs = [{"id": "1", "document": "hello world"}]

    results = simple_text_search("rust", docs)

    assert results == []
