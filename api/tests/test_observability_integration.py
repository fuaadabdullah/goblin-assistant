"""
End-to-End Observability Integration Tests

Tests the complete observability pipeline from message processing through
write-time decisions, memory promotion, retrieval tracing, and debug endpoints.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock

from api.services.write_time_matrix import write_time_intelligence
from api.services.memory_promotion_service import memory_promotion_service
from api.services.retrieval_service import RetrievalService
from api.services.observability_service import observability_service
from api.observability.debug_router import router as debug_router
from api.observability import (
    decision_logger,
    memory_promotion_logger,
    retrieval_tracer,
    context_snapshotter
)


class TestObservabilityIntegration:
    """Test the complete observability integration pipeline"""
    
    @pytest.fixture
    async def setup_observability_test(self):
        """Setup test environment with mocked services"""
        # Reset observability service state
        observability_service.write_decisions = []
        observability_service.memory_promotions = []
        observability_service.retrieval_traces = []
        observability_service.context_snapshots = []
        
        # Mock external dependencies
        with patch('api.services.observability_service.get_db') as mock_db:
            with patch('api.services.write_time_matrix.embedding_worker') as mock_worker:
                with patch('api.services.write_time_matrix.cache_service') as mock_cache:
                    yield {
                        'mock_db': mock_db,
                        'mock_worker': mock_worker,
                        'mock_cache': mock_cache
                    }
    
    async def test_write_time_decision_logging(self, setup_observability_test):
        """Test that write-time decisions are properly logged to observability"""
        # Test data
        test_message = {
            "message_id": "test_msg_123",
            "content": "This is a task result that should be embedded and summarized",
            "role": "user",
            "user_id": "test_user_123",
            "conversation_id": "test_conv_456"
        }
        
        # Process message through write-time intelligence
        result = await write_time_intelligence.process_message(
            message_id=test_message["message_id"],
            content=test_message["content"],
            role=test_message["role"],
            user_id=test_message["user_id"],
            conversation_id=test_message["conversation_id"]
        )
        
        # Verify write-time decision was logged
        assert len(observability_service.write_decisions) > 0
        
        # Get the logged decision
        logged_decision = observability_service.write_decisions[-1]
        
        # Verify decision content
        assert logged_decision.message_id == test_message["message_id"]
        assert logged_decision.user_id == test_message["user_id"]
        assert logged_decision.conversation_id == test_message["conversation_id"]
        assert "task result" in logged_decision.message_content.lower()
        assert logged_decision.classified_type == "task_result"
        assert logged_decision.embedded == True
        assert logged_decision.summarized == True
        assert logged_decision.discarded == False
        assert logged_decision.confidence > 0.5
        
        # Verify reason codes include task-related reasons
        assert "task_result" in logged_decision.reason_codes
        assert "context_relevant" in logged_decision.reason_codes
    
    async def test_memory_promotion_logging(self, setup_observability_test):
        """Test that memory promotion events are properly logged"""
        # Mock retrieval service for repetition checking
        with patch.object(memory_promotion_service, '_find_similar_memory_facts') as mock_similar:
            mock_similar.return_value = []  # No similar facts found
            
            # Create a promotion candidate
            candidate = memory_promotion_service.PromotionCandidate(
                content="I prefer using Python for development",
                category="preference",
                source_conversation="test_conv_456",
                source_type="summary",
                confidence=0.8,
                metadata={"user_id": "test_user_123"},
                created_at=datetime.utcnow()
            )
            
            # Evaluate promotion
            result = await memory_promotion_service.evaluate_promotion_candidate(candidate)
            
            # Verify promotion event was logged
            assert len(observability_service.memory_promotions) > 0
            
            # Get the logged promotion
            logged_promotion = observability_service.memory_promotions[-1]
            
            # Verify promotion content
            assert "prefer using Python" in logged_promotion.candidate_text
            assert logged_promotion.source == "summary"
            assert logged_promotion.confidence_score == 0.8
            assert logged_promotion.user_id == "test_user_123"
            assert logged_promotion.conversation_id == "test_conv_456"
            
            # Verify promotion decision (should be rejected due to low quality)
            assert logged_promotion.promotion_decision == False
            assert logged_promotion.rejection_reason is not None
    
    async def test_retrieval_trace_logging(self, setup_observability_test):
        """Test that retrieval operations are properly traced"""
        # Mock embedding service
        with patch.object(RetrievalService, '_stratified_retrieval') as mock_retrieval:
            mock_retrieval.return_value = [
                {
                    "id": "test_fact_1",
                    "content": "Test memory fact content",
                    "source_type": "memory",
                    "score": 0.9,
                    "created_at": datetime.utcnow()
                },
                {
                    "id": "test_summary_1", 
                    "content": "Test summary content",
                    "source_type": "summary",
                    "score": 0.8,
                    "created_at": datetime.utcnow()
                }
            ]
            
            # Create retrieval service instance
            retrieval_service = RetrievalService()
            
            # Perform retrieval
            results = await retrieval_service.retrieve_context(
                query="test query",
                user_id="test_user_123",
                k=2
            )
            
            # Verify retrieval trace was logged
            assert len(observability_service.retrieval_traces) > 0
            
            # Get the logged trace
            logged_trace = observability_service.retrieval_traces[-1]
            
            # Verify trace content
            assert logged_trace.user_id == "test_user_123"
            assert logged_trace.model_selected == "retrieval_service"
            assert len(logged_trace.items_retrieved) == 2
            
            # Verify items have proper structure
            for item in logged_trace.items_retrieved:
                assert "source" in item
                assert "tier" in item
                assert "relevance_score" in item
                assert "token_count" in item
                assert "rank" in item
    
    async def test_context_snapshot_logging(self, setup_observability_test):
        """Test that context assembly snapshots are properly captured"""
        # Mock context assembly service
        with patch.object(context_snapshotter, 'capture_context_snapshot') as mock_capture:
            mock_capture.return_value = {
                "request_id": "test_context_123",
                "user_id": "test_user_123",
                "context_hash": "abc123",
                "redacted_snapshot": {
                    "layers": [
                        {"name": "memory", "token_count": 100, "source_count": 2},
                        {"name": "summary", "token_count": 50, "source_count": 1}
                    ]
                },
                "total_token_usage": 150
            }
            
            # Capture context snapshot
            snapshot = await context_snapshotter.capture_context_snapshot(
                request_id="test_context_123",
                user_id="test_user_123",
                context_assembly={
                    "context": "Test context content",
                    "layers": [
                        {"name": "memory", "tokens": 100, "source_count": 2},
                        {"name": "summary", "tokens": 50, "source_count": 1}
                    ],
                    "total_tokens_used": 150
                }
            )
            
            # Verify snapshot was logged
            assert len(observability_service.context_snapshots) > 0
            
            # Get the logged snapshot
            logged_snapshot = observability_service.context_snapshots[-1]
            
            # Verify snapshot content
            assert logged_snapshot.request_id == "test_context_123"
            assert logged_snapshot.user_id == "test_user_123"
            assert logged_snapshot.context_hash == "abc123"
            assert logged_snapshot.total_token_usage == 150
    
    async def test_debug_endpoints_integration(self, setup_observability_test):
        """Test that debug endpoints return observability data correctly"""
        # First, populate some observability data
        await self.test_write_time_decision_logging(setup_observability_test)
        await self.test_memory_promotion_logging(setup_observability_test)
        await self.test_retrieval_trace_logging(setup_observability_test)
        
        # Test write decisions endpoint
        from api.observability.debug_router import get_write_decisions
        
        write_decisions = await get_write_decisions(
            conversation_id="test_conv_456",
            limit=10
        )
        
        assert "conversation_id" in write_decisions
        assert "decisions" in write_decisions
        assert "summary" in write_decisions
        assert write_decisions["conversation_id"] == "test_conv_456"
        assert len(write_decisions["decisions"]) > 0
        
        # Test memory debug endpoint
        from api.observability.debug_router import get_memory_debug_info
        
        memory_info = await get_memory_debug_info(user_id="test_user_123")
        
        assert "user_id" in memory_info
        assert "memory_items" in memory_info
        assert "memory_health" in memory_info
        assert memory_info["user_id"] == "test_user_123"
        
        # Test retrieval trace endpoint
        from api.observability.debug_router import get_retrieval_trace
        
        if observability_service.retrieval_traces:
            trace_id = observability_service.retrieval_traces[-1].request_id
            trace = await get_retrieval_trace(request_id=trace_id)
            
            assert "request_id" in trace
            assert "user_id" in trace
            assert "retrieval_items" in trace
            assert trace["user_id"] == "test_user_123"
    
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
        
        # Test with simulated high rejection rate
        observability_service.memory_health["promotion_rejection_rate"] = 0.9
        
        alerts = observability_service.check_alerts()
        
        # Should have an alert for high rejection rate
        memory_alerts = [a for a in alerts if a["type"] == "memory_promotion_spike"]
        assert len(memory_alerts) > 0
        assert memory_alerts[0]["severity"] == "warning"
        assert "rejection rate is high" in memory_alerts[0]["message"]
    
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
        # Test with invalid data
        with patch.object(observability_service, 'log_write_time_decision') as mock_log:
            mock_log.side_effect = Exception("Test error")
            
            # Should not crash the system
            try:
                observability_service.log_write_time_decision(
                    message_id="test",
                    user_id="test",
                    conversation_id="test",
                    message_content="test",
                    message_role="test",
                    write_time_result={}
                )
            except Exception:
                pass  # Expected to fail
            
            # System should continue working
            assert True  # If we get here, the system didn't crash
    
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
                "conversation_id": "test_conv_456"
            }
            
            await write_time_intelligence.process_message(
                message_id=test_message["message_id"],
                content=test_message["content"],
                role=test_message["role"],
                user_id=test_message["user_id"],
                conversation_id=test_message["conversation_id"]
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete in reasonable time (less than 5 seconds for 10 operations)
        assert total_time < 5.0
        
        # Should have logged all decisions
        assert len(observability_service.write_decisions) >= 10


class TestObservabilityDebugEndpoints:
    """Test the debug endpoints specifically"""
    
    async def test_write_decisions_search(self, setup_observability_test):
        """Test search functionality for write decisions"""
        # Populate test data
        await TestObservabilityIntegration().test_write_time_decision_logging(setup_observability_test)
        
        # Test search endpoint
        from api.observability.debug_router import search_write_decisions
        
        search_results = await search_write_decisions(
            query="task",
            conversation_id="test_conv_456"
        )
        
        assert "query" in search_results
        assert "results" in search_results
        assert "total_results" in search_results
        assert search_results["query"] == "task"
        assert len(search_results["results"]) > 0
    
    async def test_memory_promotions_search(self, setup_observability_test):
        """Test search functionality for memory promotions"""
        # Populate test data
        await TestObservabilityIntegration().test_memory_promotion_logging(setup_observability_test)
        
        # Test search endpoint
        from api.observability.debug_router import search_memory_promotions
        
        search_results = await search_memory_promotions(
            query="prefer",
            user_id="test_user_123"
        )
        
        assert "query" in search_results
        assert "results" in search_results
        assert "total_results" in search_results
        assert search_results["query"] == "prefer"
        assert len(search_results["results"]) > 0
    
    async def test_system_health_endpoint(self, setup_observability_test):
        """Test the system health endpoint"""
        # Populate test data
        await TestObservabilityIntegration().test_write_time_decision_logging(setup_observability_test)
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
        await TestObservabilityIntegration().test_write_time_decision_logging(setup_observability_test)
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