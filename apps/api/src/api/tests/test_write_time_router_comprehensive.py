"""Tests for write_time_router module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.write_time_router import TEST_MESSAGES, router


@pytest.fixture
def app():
    """Create a FastAPI test app with write_time router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create a TestClient for the app."""
    return TestClient(app)


class TestMessageProcessing:
    """Tests for message processing endpoint."""

    def test_test_message_processing_success(self, client):
        """Test successful message processing."""
        with patch("api.write_time_router._get_write_time_intelligence") as mock_get:
            mock_intelligence = AsyncMock()
            mock_get.return_value = mock_intelligence

            mock_intelligence.process_message.return_value = {
                "message_id": "test_123",
                "classification": {"type": "chat", "confidence": 0.95},
                "decision": {"action": "store", "priority": "high"},
                "execution": {"status": "success"},
                "processed_at": datetime.utcnow().isoformat(),
            }

            request_data = {
                "content": "How are you doing?",
                "role": "user",
                "user_id": "user_123",
            }

            response = client.post("/api/v1/write-time/test", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["message_id"] == "test_123"
            assert data["classification"]["type"] == "chat"

    def test_message_processing_exception(self, client):
        """Test message processing with exception."""
        with patch("api.write_time_router._get_write_time_intelligence") as mock_get:
            mock_intelligence = AsyncMock()
            mock_get.return_value = mock_intelligence
            mock_intelligence.process_message.side_effect = Exception("Processing failed")

            response = client.post("/api/v1/write-time/test", json={"content": "test"})

            assert response.status_code == 500
            assert response.json()["detail"] == "Test processing failed: Processing failed"


class TestCacheStatsEndpoint:
    """Tests for cache stats endpoint."""

    def test_cache_stats_success(self, client):
        """Test cache stats retrieval."""
        with patch("api.write_time_router.cache_service") as mock_cache:
            mock_cache.get_cache_stats = AsyncMock(
                return_value={
                    "status": "healthy",
                    "cache_stats": {"total_keys": 150},
                    "redis_info": {"used_memory_human": "25 MB"},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            response = client.get("/api/v1/write-time/cache/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["cache_stats"]["total_keys"] == 150

    def test_cache_stats_exception(self, client):
        """Test cache stats with exception."""
        with patch("api.write_time_router.cache_service") as mock_cache:
            mock_cache.get_cache_stats = AsyncMock(side_effect=Exception("Redis connection failed"))

            response = client.get("/api/v1/write-time/cache/stats")

            assert response.status_code == 500
            assert response.json()["detail"] == "Failed to get cache stats: Redis connection failed"


class TestCacheCleanupEndpoint:
    """Tests for cache cleanup endpoint."""

    def test_cache_cleanup_success(self, client):
        """Test cache cleanup."""
        with patch("api.write_time_router.cache_service") as mock_cache:
            mock_cache.cleanup_expired_keys = AsyncMock(
                return_value={
                    "status": "success",
                    "message": "Cleaned up 45 keys",
                }
            )

            response = client.post("/api/v1/write-time/cache/cleanup")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_cache_cleanup_exception(self, client):
        """Test cache cleanup with exception."""
        with patch("api.write_time_router.cache_service") as mock_cache:
            mock_cache.cleanup_expired_keys = AsyncMock(side_effect=Exception("Cleanup failed"))

            response = client.post("/api/v1/write-time/cache/cleanup")

            assert response.status_code == 500
            assert response.json()["detail"] == "Cache cleanup failed: Cleanup failed"


class TestDecisionMatrixConfigEndpoint:
    """Tests for decision matrix config endpoint."""

    def test_decision_matrix_config(self, client):
        """Test decision matrix config retrieval."""
        with patch("api.write_time_router._get_write_time_decision_matrix") as mock_get:
            mock_matrix_class = MagicMock()
            mock_instance = MagicMock()
            mock_matrix_class.return_value = mock_instance

            mock_instance.DECISION_TABLE = {
                "chat": {"priority": "low"},
                "fact": {"priority": "high"},
            }
            mock_instance.MAX_EMBEDDINGS_PER_HOUR = 100
            mock_instance.MAX_SUMMARIES_PER_DAY = 50
            mock_instance.MAX_CACHE_SIZE_MB = 1000

            mock_get.return_value = mock_matrix_class

            response = client.get("/api/v1/write-time/matrix/config")

            assert response.status_code == 200
            data = response.json()
            assert "decision_table" in data
            assert data["rate_limits"]["max_embeddings_per_hour"] == 100

    def test_decision_matrix_exception(self, client):
        """Test decision matrix with exception."""
        with patch("api.write_time_router._get_write_time_decision_matrix") as mock_get:
            mock_get.side_effect = Exception("Matrix load failed")

            response = client.get("/api/v1/write-time/matrix/config")

            assert response.status_code == 500
            assert response.json()["detail"] == "Failed to get matrix config: Matrix load failed"


class TestWriteTimeMetricsEndpoint:
    """Tests for write-time metrics endpoint."""

    def test_write_time_metrics(self, client):
        """Test metrics retrieval."""
        with (
            patch("api.write_time_router.cache_service") as mock_cache,
            patch("api.write_time_router._get_write_time_decision_matrix") as mock_get,
        ):
            mock_cache.get_cache_stats = AsyncMock(
                return_value={
                    "status": "healthy",
                    "cache_stats": {
                        "total_keys": 100,
                        "message_keys": 50,
                        "context_keys": 30,
                        "preference_keys": 20,
                    },
                }
            )

            mock_matrix_class = MagicMock()
            mock_instance = MagicMock()
            mock_matrix_class.return_value = mock_instance

            mock_instance.MAX_EMBEDDINGS_PER_HOUR = 100
            mock_instance.MAX_SUMMARIES_PER_DAY = 50
            mock_instance._embedding_counts = {"used": 45}
            mock_instance._summary_counts = {"used": 10}
            mock_instance.DECISION_TABLE = {"chat": {}, "fact": {}}

            mock_get.return_value = mock_matrix_class

            response = client.get("/api/v1/write-time/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data["cache"]["total_keys"] == 100


class TestCacheClearEndpoint:
    """Tests for cache clear endpoint."""

    def test_cache_clear_success(self, client):
        """Test cache clear."""
        with patch("api.write_time_router.cache_service") as mock_cache:
            mock_cache.flush = AsyncMock(return_value=True)

            response = client.post("/api/v1/write-time/cache/clear")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_cache_clear_failure(self, client):
        """Test cache clear failure."""
        with patch("api.write_time_router.cache_service") as mock_cache:
            mock_cache.flush = AsyncMock(return_value=False)

            response = client.post("/api/v1/write-time/cache/clear")

            assert response.status_code == 500
            assert response.json()["detail"] == "Failed to clear cache"


class TestTestExamplesEndpoint:
    """Tests for test examples endpoint."""

    def test_test_examples(self, client):
        """Test examples endpoint."""
        response = client.get("/api/v1/write-time/test/examples")

        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert "timestamp" in data

        examples = data["examples"]
        required = ["chat", "fact", "preference", "task_result", "system", "noise"]
        for category in required:
            assert category in examples
            assert isinstance(examples[category], list)
            assert len(examples[category]) > 0


class TestBatchProcessingEndpoint:
    """Tests for batch processing endpoint."""

    def test_batch_processing_success(self, client):
        """Test batch message processing."""
        with patch("api.write_time_router._get_write_time_intelligence") as mock_get:
            mock_intelligence = AsyncMock()
            mock_get.return_value = mock_intelligence

            mock_intelligence.process_message.side_effect = [
                {
                    "message_id": "batch_0",
                    "classification": {"type": "chat"},
                    "decision": {"action": "store"},
                    "execution": {"actions_executed": ["store"]},
                    "processed_at": datetime.utcnow().isoformat(),
                },
                {
                    "message_id": "batch_1",
                    "classification": {"type": "fact"},
                    "decision": {"action": "store_and_embed"},
                    "execution": {"actions_executed": ["store", "embed"]},
                    "processed_at": datetime.utcnow().isoformat(),
                },
            ]

            request_data = [
                {"content": "Hello", "role": "user"},
                {"content": "I am a developer", "role": "user"},
            ]

            response = client.post("/api/v1/write-time/test/batch", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["total_messages"] == 2
            assert len(data["results"]) == 2

    def test_batch_processing_empty(self, client):
        """Test batch with empty list."""
        with patch("api.write_time_router._get_write_time_intelligence") as mock_get:
            mock_intelligence = AsyncMock()
            mock_get.return_value = mock_intelligence

            response = client.post("/api/v1/write-time/test/batch", json=[])

            assert response.status_code == 200
            data = response.json()
            assert data["total_messages"] == 0

    def test_batch_processing_exception(self, client):
        """Test batch processing with exception."""
        with patch("api.write_time_router._get_write_time_intelligence") as mock_get:
            mock_intelligence = AsyncMock()
            mock_get.return_value = mock_intelligence
            mock_intelligence.process_message.side_effect = Exception("Batch failure")

            response = client.post(
                "/api/v1/write-time/test/batch",
                json=[{"content": "Hello", "role": "user"}],
            )

            assert response.status_code == 500
            assert response.json()["detail"] == "Batch testing failed: Batch failure"


class TestConstantData:
    """Tests for constant data."""

    def test_test_messages_structure(self):
        """Test TEST_MESSAGES structure."""
        assert isinstance(TEST_MESSAGES, dict)

        required = ["chat", "fact", "preference", "task_result", "system"]
        for category in required:
            assert category in TEST_MESSAGES
            assert isinstance(TEST_MESSAGES[category], list)
            assert len(TEST_MESSAGES[category]) > 0

            for message in TEST_MESSAGES[category]:
                assert isinstance(message, str)
                assert len(message) > 0
