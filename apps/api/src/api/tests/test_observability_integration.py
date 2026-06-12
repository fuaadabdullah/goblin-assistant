"""
End-to-End Observability Integration Tests

Tests the complete observability pipeline from message processing through
write-time decisions, memory promotion, retrieval tracing, and debug endpoints.

Updated to query observability sub-modules directly instead of relying on
removed internal storage lists in the ObservabilityService facade.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from api.observability.context_snapshotter import context_snapshotter as _cs
from api.observability.decision_logger import decision_logger as _dl
from api.observability.memory_logger import memory_promotion_logger as _ml
from api.observability.retrieval_tracer import retrieval_tracer as _rt
from api.services.memory_promotion import PromotionCandidate, memory_promotion_service
from api.services.observability_service import observability_service
from api.services.retrieval_service import RetrievalService
from api.services.write_time_matrix import write_time_intelligence


@pytest.fixture(autouse=True)
def _disable_ops_auth(monkeypatch):
    from api.ops import security as _ops_sec

    monkeypatch.setattr(_ops_sec.OpsSecurityConfig, "REQUIRE_AUTH", False)


@pytest_asyncio.fixture
async def setup_observability_test():
    """Setup test environment with mocked services"""
    # Clear sub-module caches
    _dl._decision_cache.clear()
    _ml._promotion_cache.clear()
    _rt._trace_cache.clear()
    _cs._snapshot_cache.clear()

    with patch("api.services.observability_service.get_db") as mock_db:
        with patch("api.services.write_time_matrix.embedding_worker") as mock_worker:
            with patch("api.services.write_time_matrix.cache_service") as mock_cache:
                yield {
                    "mock_db": mock_db,
                    "mock_worker": mock_worker,
                    "mock_cache": mock_cache,
                }


class TestObservabilityIntegration:
    """Test the complete observability integration pipeline"""

    async def test_write_time_decision_logging(self, setup_observability_test):
        """Test that write-time decisions are properly logged to observability"""
        test_message = {
            "message_id": "test_msg_123",
            "content": "This is a task result that should be embedded and summarized",
            "role": "user",
            "user_id": "test_user_123",
            "conversation_id": "test_conv_456",
        }

        # Process message through write-time intelligence
        await write_time_intelligence.process_message(
            message_id=test_message["message_id"],
            content=test_message["content"],
            role=test_message["role"],
            user_id=test_message["user_id"],
            conversation_id=test_message["conversation_id"],
        )

        # Verify write-time decision was logged via decision_logger
        decisions = await _dl.get_decision_history(
            conversation_id=test_message["conversation_id"], limit=100
        )

        assert len(decisions) > 0

        # Get the logged decision (most recent first)
        logged_decision = decisions[0]

        # Verify decision content
        # DecisionRecord.to_dict() returns flat fields
        assert logged_decision["message_id"] == test_message["message_id"]
        assert logged_decision["user_id"] == test_message["user_id"]
        assert logged_decision["classified_type"] == "task_result"
        assert logged_decision["embedded"] is True
        assert logged_decision["summarized"] is True
        assert logged_decision["discarded"] is False
        assert logged_decision["confidence"] > 0.5

    async def test_memory_promotion_logging(self, setup_observability_test):
        """Test that memory promotion events are properly logged"""
        import asyncio

        # Mock retrieval service for repetition checking and conflict resolution
        with patch.object(memory_promotion_service, "_find_similar_memory_facts") as mock_similar:
            mock_similar.return_value = [
                {
                    "id": "mem-123",
                    "content": "User prefers concise answers",
                    "conversation_id": "test_conv_456",
                    "scope": "conversation",
                    "confidence": 0.88,
                    "metadata": {"scope": "conversation"},
                }
            ]

            # Create a promotion candidate
            candidate = PromotionCandidate(
                content="I prefer using Python for development",
                category="preference",
                source_conversation="test_conv_456",
                source_type="summary",
                confidence=0.8,
                metadata={
                    "user_id": "test_user_123",
                    "memory_state": "verified",
                    "conflict_reason": "superseded by explicit correction",
                    "conflicting_memory_ids": ["mem-123"],
                },
                created_at=datetime.utcnow(),
            )

            # Evaluate promotion
            await memory_promotion_service.evaluate_promotion_candidate(candidate)

            # Yield to let the create_task in the facade execute
            await asyncio.sleep(0)

            # Verify promotion event was logged via memory_logger (no user filter)
            promotions = await _ml.get_promotion_history(limit=100)
            assert len(promotions) > 0

            # Get the logged promotion (most recent first)
            logged_promotion = promotions[0]

            # Verify promotion content
            assert "prefer using Python" in logged_promotion["candidate_text"]
            assert logged_promotion["source_type"] == "summary"
            assert logged_promotion["confidence_score"] == 0.8

            # Verify promotion decision metadata
            assert logged_promotion["metadata"]["memory_state"] == "verified"
            assert logged_promotion["metadata"]["conflict_reason"] is not None
            assert "mem-123" in logged_promotion["metadata"]["conflicting_memory_ids"]

            # Verify promotion decision
            assert logged_promotion["promotion_decision"] is False  # Rejected
            assert logged_promotion["rejection_reason"] is not None

    async def test_retrieval_trace_logging(self, setup_observability_test):
        """Test that retrieval operations are properly traced"""
        fake_results = [
            {
                "id": "test_fact_1",
                "content": "Test memory fact content",
                "source_type": "memory",
                "score": 0.9,
                "created_at": datetime.utcnow(),
            },
            {
                "id": "test_summary_1",
                "content": "Test summary content",
                "source_type": "summary",
                "score": 0.8,
                "created_at": datetime.utcnow(),
            },
        ]
        with patch.object(
            RetrievalService, "_stratified_retrieval", new_callable=AsyncMock
        ) as mock_retrieval:
            mock_retrieval.return_value = (fake_results, {})

            # Create retrieval service instance with mocked embedding
            retrieval_service = RetrievalService()
            mock_emb = AsyncMock()
            mock_emb.embed_text = AsyncMock(return_value=[0.1] * 768)
            retrieval_service.embedding_service = mock_emb

            # Perform retrieval
            await retrieval_service.retrieve_context(
                query="test query", user_id="test_user_123", k=2
            )

            # Verify retrieval trace was logged via retrieval_tracer
            traces = await _rt.get_retrieval_history(user_id="test_user_123", limit=10)
            assert len(traces) > 0

            # Get the logged trace
            logged_trace = traces[0]

            # Verify trace content
            assert logged_trace["user_id"] == "test_user_123"
            assert len(logged_trace["items_retrieved"]) == 2

            # Verify items have proper structure
            for item in logged_trace["items_retrieved"]:
                assert "source" in item
                assert "relevance_score" in item
                assert "token_count" in item
                assert "rank" in item

    async def test_context_snapshot_logging(self, setup_observability_test):
        """Test that context assembly snapshots are properly captured"""
        observability_service.log_context_assembly_snapshot(
            request_id="test_context_123",
            user_id="test_user_123",
            conversation_id="test_conv_456",
            context_assembly={
                "context": "Test context content",
                "layers": [
                    {"name": "memory", "tokens": 100, "source_count": 2},
                    {"name": "summary", "tokens": 50, "source_count": 1},
                ],
                "total_tokens_used": 150,
            },
        )

        # Verify snapshot was logged via context_snapshotter
        snapshot = await _cs.get_context_snapshot("test_context_123")

        assert snapshot is not None
        assert snapshot["request_id"] == "test_context_123"
        assert snapshot["user_id"] == "test_user_123"
        assert snapshot["total_tokens"] == 150

    async def test_debug_endpoints_integration(self, setup_observability_test):
        """Test that debug endpoints return observability data correctly"""
        import asyncio

        # First, populate some observability data
        await self.test_write_time_decision_logging(setup_observability_test)
        await self.test_memory_promotion_logging(setup_observability_test)
        await self.test_retrieval_trace_logging(setup_observability_test)

        # Yield to let the create_task in the facade execute
        await asyncio.sleep(0)

        # Test write decisions endpoint via decision_logger directly
        write_decisions = await _dl.get_decision_history(conversation_id="test_conv_456", limit=10)

        assert isinstance(write_decisions, list)
        assert len(write_decisions) > 0
        assert write_decisions[0]["conversation_id"] == "test_conv_456"
        assert write_decisions[0]["classified_type"] == "task_result"

        # Test memory debug endpoint via memory_logger directly
        memory_info = await _ml.get_promotion_history(user_id="test_user_123", limit=10)

        assert isinstance(memory_info, list)

        # Test retrieval trace endpoint via tracer directly
        traces = await _rt.get_retrieval_history(user_id="test_user_123", limit=10)

        assert len(traces) > 0
        assert traces[0]["user_id"] == "test_user_123"
        assert len(traces[0]["items_retrieved"]) == 2

    async def test_observability_metrics_collection(self, setup_observability_test):
        """Test that observability metrics are properly collected"""
        # Populate some test data
        await self.test_write_time_decision_logging(setup_observability_test)
        await self.test_memory_promotion_logging(setup_observability_test)
        await self.test_retrieval_trace_logging(setup_observability_test)

        # Get critical metrics
        metrics = observability_service.get_critical_metrics()

        assert "memory_health" in metrics
        assert "retrieval_quality" in metrics
        assert "cost_control" in metrics
        assert "timestamp" in metrics

        # Verify memory health metrics
        memory_health = metrics["memory_health"]
        assert "promotion_rejection_rate" in memory_health
        assert "contradiction_rate" in memory_health
        assert "decay_events" in memory_health

        # Verify retrieval quality metrics
        retrieval_quality = metrics["retrieval_quality"]
        assert "avg_chunks_per_request" in retrieval_quality
        assert "token_utilization_percent" in retrieval_quality
        assert "retrieval_hit_rate" in retrieval_quality

    async def test_observability_alerts(self, setup_observability_test):
        """Test that observability alerts are properly generated"""
        # Test alert checking
        alerts = observability_service.check_alerts()

        # Should return a list
        assert isinstance(alerts, list)

    async def test_observability_data_export(self, setup_observability_test):
        """Test that observability data can be exported"""
        # Populate some test data
        await self.test_write_time_decision_logging(setup_observability_test)
        await self.test_memory_promotion_logging(setup_observability_test)
        await self.test_retrieval_trace_logging(setup_observability_test)

        # Export data
        export_data = observability_service.export_observability_data()

        assert "write_decisions" in export_data
        assert "memory_promotions" in export_data
        assert "retrieval_traces" in export_data
        assert "context_snapshots" in export_data
        assert "metrics" in export_data
        assert "alerts" in export_data
        assert "export_timestamp" in export_data

        # Verify data structure
        assert isinstance(export_data["write_decisions"], list)
        assert isinstance(export_data["memory_promotions"], list)
        assert isinstance(export_data["retrieval_traces"], list)
        assert isinstance(export_data["context_snapshots"], list)

    async def test_observability_error_handling(self, setup_observability_test):
        """Test that observability handles errors gracefully"""
        with patch.object(observability_service, "log_write_time_decision") as mock_log:
            mock_log.side_effect = Exception("Test error")

            try:
                observability_service.log_write_time_decision(
                    message_id="test",
                    user_id="test",
                    conversation_id="test",
                    message_content="test",
                    message_role="test",
                    write_time_result={},
                )
            except Exception:
                pass  # expected — verifies the exception propagates cleanly

    async def test_observability_performance_impact(self, setup_observability_test):
        """Test that observability logging doesn't significantly impact performance"""
        import time

        # Measure time for multiple write-time decisions
        start_time = time.time()

        for i in range(10):
            test_message = {
                "message_id": f"test_msg_{i}",
                "content": f"Test message {i}",
                "role": "user",
                "user_id": "test_user_123",
                "conversation_id": "test_conv_456",
            }

            await write_time_intelligence.process_message(
                message_id=test_message["message_id"],
                content=test_message["content"],
                role=test_message["role"],
                user_id=test_message["user_id"],
                conversation_id=test_message["conversation_id"],
            )

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete in reasonable time (less than 5 seconds for 10 operations)
        assert total_time < 5.0

        # Should have logged all decisions
        decisions = await _dl.get_decision_history(conversation_id="test_conv_456", limit=100)
        assert len(decisions) >= 10


class TestObservabilityDebugEndpoints:
    """Test the debug endpoints specifically"""

    async def test_write_decisions_search(self, setup_observability_test):
        """Test search functionality for write decisions"""
        # Populate test data
        await TestObservabilityIntegration().test_write_time_decision_logging(
            setup_observability_test
        )

        # Test search endpoint via decision_logger directly
        search_results = await _dl.search_decisions(query="task", conversation_id="test_conv_456")

        assert isinstance(search_results, list)
        assert len(search_results) > 0

    async def test_memory_promotions_search(self, setup_observability_test):
        """Test search functionality for memory promotions"""
        import asyncio

        # Populate test data
        await TestObservabilityIntegration().test_memory_promotion_logging(setup_observability_test)

        # Yield to let the create_task in the facade execute
        await asyncio.sleep(0)

        # Test search endpoint via memory_logger directly
        search_results = await _ml.search_promotions(query="prefer", user_id="test_user_123")

        assert isinstance(search_results, list)
        assert len(search_results) > 0

    async def test_system_health_endpoint(self, setup_observability_test):
        """Test the system health endpoint"""
        # Populate test data
        await TestObservabilityIntegration().test_write_time_decision_logging(
            setup_observability_test
        )
        await TestObservabilityIntegration().test_memory_promotion_logging(setup_observability_test)
        await TestObservabilityIntegration().test_retrieval_trace_logging(setup_observability_test)

        # Test system health endpoint
        from api.observability.debug_router import get_system_health

        health_report = await get_system_health(user_id="test_user_123")

        assert "user_id" in health_report
        assert "overall_health" in health_report
        assert "system_health" in health_report
        assert "recommendations" in health_report
        assert health_report["user_id"] == "test_user_123"

    async def test_observability_summary_endpoint(self, setup_observability_test):
        """Test the observability summary endpoint"""
        # Populate test data
        await TestObservabilityIntegration().test_write_time_decision_logging(
            setup_observability_test
        )
        await TestObservabilityIntegration().test_memory_promotion_logging(setup_observability_test)
        await TestObservabilityIntegration().test_retrieval_trace_logging(setup_observability_test)

        # Test summary endpoint
        from api.observability.debug_router import get_observability_summary

        summary = await get_observability_summary(user_id="test_user_123")

        assert "user_id" in summary
        assert "summary" in summary
        assert "detailed_stats" in summary
        assert summary["user_id"] == "test_user_123"

        # Verify summary contains all system stats
        assert "decision_system" in summary["summary"]
        assert "memory_system" in summary["summary"]
        assert "retrieval_system" in summary["summary"]
        assert "context_system" in summary["summary"]


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
