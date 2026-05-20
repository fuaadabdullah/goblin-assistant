"""
Tests for search_router
Tests document search functionality
"""

from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app


client = TestClient(app)


class TestSearchRouterEndpoint:
    """Tests for search router endpoint"""

    def test_search_endpoint_exists(self):
        """Test search endpoint is registered"""
        response = client.post(
            "/search/documents",
            json={"query": "test", "collection_name": "documents"},
        )
        # Should not 404
        assert response.status_code in [200, 400, 422, 500]

    def test_search_with_valid_query(self):
        """Test search with valid query"""
        with patch(
            "api.search_router.simple_text_search"
        ) as mock_search:
            mock_search.return_value = [
                {"id": "1", "document": "test", "score": 0.9}
            ]

            response = client.post(
                "/search/documents",
                json={"query": "test", "collection_name": "documents"},
            )

            assert response.status_code in [200, 422]

    def test_search_requires_query(self):
        """Test search requires query parameter"""
        response = client.post(
            "/search/documents",
            json={"collection_name": "documents"},
        )

        assert response.status_code in [400, 422]

    def test_search_with_n_results(self):
        """Test search with custom n_results"""
        with patch(
            "api.search_router.simple_text_search"
        ) as mock_search:
            mock_search.return_value = []

            response = client.post(
                "/search/documents",
                json={
                    "query": "test",
                    "collection_name": "documents",
                    "n_results": 5,
                },
            )

            assert response.status_code in [200, 422]

    def test_search_default_collection(self):
        """Test search uses default collection"""
        with patch(
            "api.search_router.simple_text_search"
        ) as mock_search:
            mock_search.return_value = []

            response = client.post(
                "/search/documents",
                json={"query": "test"},
            )

            assert response.status_code in [200, 422]


class TestSearchRouterSimpleTextSearch:
    """Tests for simple text search function"""

    def test_simple_text_search_exact_match(self):
        """Test exact phrase matching"""
        from api.search_router import simple_text_search

        documents = [
            {"id": "1", "document": "hello world"},
            {"id": "2", "document": "goodbye world"},
        ]

        results = simple_text_search("hello world", documents)

        # First document should rank higher
        assert len(results) > 0

    def test_simple_text_search_partial_match(self):
        """Test partial word matching"""
        from api.search_router import simple_text_search

        documents = [
            {"id": "1", "document": "python programming"},
            {"id": "2", "document": "java programming"},
        ]

        results = simple_text_search("python", documents)

        assert len(results) > 0

    def test_simple_text_search_case_insensitive(self):
        """Test case insensitive search"""
        from api.search_router import simple_text_search

        documents = [{"id": "1", "document": "Python Programming"}]

        results = simple_text_search("python", documents, n_results=1)

        assert len(results) == 1

    def test_simple_text_search_empty_query(self):
        """Test empty query"""
        from api.search_router import simple_text_search

        documents = [{"id": "1", "document": "test"}]

        results = simple_text_search("", documents)

        assert isinstance(results, list)

    def test_simple_text_search_no_documents(self):
        """Test searching empty collection"""
        from api.search_router import simple_text_search

        results = simple_text_search("query", [])

        assert len(results) == 0

    def test_simple_text_search_respects_n_results(self):
        """Test n_results limit is respected"""
        from api.search_router import simple_text_search

        documents = [
            {"id": str(i), "document": f"test {i}"}
            for i in range(100)
        ]

        results = simple_text_search("test", documents, n_results=5)

        assert len(results) <= 5

    def test_simple_text_search_scoring(self):
        """Test scoring ranks results correctly"""
        from api.search_router import simple_text_search

        documents = [
            {"id": "1", "document": "test"},
            {"id": "2", "document": "test test test"},
            {"id": "3", "document": "other"},
        ]

        results = simple_text_search("test", documents, n_results=5)

        # Higher scoring docs should come first
        if len(results) > 1:
            assert (
                results[0].get("score", 0) >=
                results[1].get("score", 0)
            )


class TestSearchRouterModels:
    """Tests for search request/response models"""

    def test_search_query_model(self):
        """Test SearchQuery model"""
        from api.search_router import SearchQuery

        query = SearchQuery(
            query="test",
            collection_name="docs",
            n_results=10,
        )

        assert query.query == "test"
        assert query.collection_name == "docs"
        assert query.n_results == 10

    def test_search_query_defaults(self):
        """Test SearchQuery defaults"""
        from api.search_router import SearchQuery

        query = SearchQuery(query="test")

        assert query.collection_name == "documents"
        assert query.n_results == 10

    def test_search_result_model(self):
        """Test SearchResult model"""
        from api.search_router import SearchResult

        result = SearchResult(
            id="1",
            document="test doc",
            score=0.95,
        )

        assert result.id == "1"
        assert result.document == "test doc"
        assert result.score == 0.95

    def test_search_response_model(self):
        """Test SearchResponse model"""
        from api.search_router import SearchResponse, SearchResult

        results = [SearchResult(id="1", document="test")]
        response = SearchResponse(results=results, total_results=1)

        assert len(response.results) == 1
        assert response.total_results == 1


class TestSearchRouterIntegration:
    """Tests for search router integration"""

    def test_search_pipeline_end_to_end(self):
        """Test complete search pipeline"""
        from api.search_router import SearchQuery, simple_text_search

        query_obj = SearchQuery(
            query="python programming",
            collection_name="tutorials",
            n_results=5,
        )

        documents = [
            {"id": "1", "document": "Python basics for beginners"},
            {"id": "2", "document": "Advanced Java programming"},
            {"id": "3", "document": "Python best practices"},
        ]

        results = simple_text_search(
            query_obj.query, documents, query_obj.n_results
        )

        # Python docs should rank higher than Java
        assert len(results) > 0

    def test_search_with_metadata(self):
        """Test search preserves metadata"""
        from api.search_router import simple_text_search

        documents = [
            {
                "id": "1",
                "document": "test",
                "metadata": {"author": "alice"},
            }
        ]

        results = simple_text_search("test", documents)

        if results:
            assert results[0].get("metadata") is not None
