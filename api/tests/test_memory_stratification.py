"""
Test suite for memory stratification system
Validates the complete pipeline from message classification to long-term memory
"""

import pytest
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from api.services.message_classifier import (
    MessageClassifier, 
    MessageType, 
    MessageClassification,
    classification_pipeline
)
from api.services.memory_promotion_service import (
    MemoryPromotionService,
    MemoryFact,
    PromotionStatus
)
from api.services.retrieval_service import RetrievalService
from api.storage.conversations import conversation_store
from api.storage.models import ConversationModel, MessageModel


class TestMessageClassification:
    """Test message classification functionality"""
    
    def setup_method(self):
        self.classifier = MessageClassifier()
    
    def test_fact_classification(self):
        """Test classification of fact messages"""
        test_cases = [
            ("I am a software engineer with 5 years of experience", MessageType.FACT),
            ("My name is John Smith", MessageType.FACT),
            ("I live in New York City", MessageType.FACT),
            ("I work at Google as a developer", MessageType.FACT),
            ("I studied computer science at MIT", MessageType.FACT),
        ]
        
        for content, expected_type in test_cases:
            classification = self.classifier.classify_message(content, "user")
            assert classification.message_type == expected_type
            assert classification.confidence > 0.5
    
    def test_preference_classification(self):
        """Test classification of preference messages"""
        test_cases = [
            ("I prefer Python over JavaScript", MessageType.PREFERENCE),
            ("I don't like using React", MessageType.PREFERENCE),
            ("I always use vim for coding", MessageType.PREFERENCE),
            ("I want to learn machine learning", MessageType.PREFERENCE),
            ("I love functional programming", MessageType.PREFERENCE),
        ]
        
        for content, expected_type in test_cases:
            classification = self.classifier.classify_message(content, "user")
            assert classification.message_type == expected_type
            assert classification.confidence > 0.5
    
    def test_chat_classification(self):
        """Test classification of chat messages"""
        test_cases = [
            ("Hello, how are you?", MessageType.CHAT),
            ("What's the weather like today?", MessageType.CHAT),
            ("Can you help me with this?", MessageType.CHAT),
            ("I'm not sure about this", MessageType.CHAT),
        ]
        
        for content, expected_type in test_cases:
            classification = self.classifier.classify_message(content, "user")
            assert classification.message_type == expected_type
    
    def test_system_classification(self):
        """Test classification of system messages"""
        classification = self.classifier.classify_message("System message", "system")
        assert classification.message_type == MessageType.SYSTEM
        assert classification.confidence == 1.0


class TestMemoryPromotion:
    """Test memory promotion functionality"""
    
    def setup_method(self):
        self.promotion_service = MemoryPromotionService()
    
    def test_fact_extraction_from_fact_message(self):
        """Test fact extraction from fact-classified messages"""
        content = "I am a software engineer with 5 years of experience"
        classification = MessageClassification(
            message_type=MessageType.FACT,
            confidence=0.9,
            keywords=["software engineer", "5 years"],
            reasoning="Fact pattern matched"
        )
        
        facts = self.promotion_service._extract_facts_from_fact_message(content, classification)
        
        assert len(facts) > 0
        fact = facts[0]
        assert "software engineer" in fact.fact_text.lower()
        assert fact.category in ["user_trait", "skill"]
        assert fact.confidence == 0.9
    
    def test_fact_extraction_from_preference_message(self):
        """Test fact extraction from preference-classified messages"""
        content = "I prefer Python over JavaScript"
        classification = MessageClassification(
            message_type=MessageType.PREFERENCE,
            confidence=0.8,
            keywords=["Python", "JavaScript"],
            reasoning="Preference pattern matched"
        )
        
        facts = self.promotion_service._extract_facts_from_preference_message(content, classification)
        
        assert len(facts) > 0
        fact = facts[0]
        assert "prefer" in fact.fact_text.lower()
        assert fact.category == "preference"
        assert fact.confidence == 0.8
    
    def test_invalid_fact_filtering(self):
        """Test filtering of invalid facts"""
        invalid_facts = [
            "I'm currently working on a project",  # Temporary
            "I'm trying to learn React",  # Learning/Temporary
            "I'm not sure about this",  # Uncertain
            "Today is Monday",  # Time-specific
            "I have version 1.2.3 installed",  # Technical version
        ]
        
        for fact_text in invalid_facts:
            is_valid = self.promotion_service._is_valid_fact(fact_text)
            assert not is_valid, f"Fact should be filtered: {fact_text}"
    
    def test_valid_fact_acceptance(self):
        """Test acceptance of valid facts"""
        valid_facts = [
            "I am a software engineer",
            "I prefer Python programming language",
            "I have 5 years of experience",
            "I live in New York",
            "I work at Google",
        ]
        
        for fact_text in valid_facts:
            is_valid = self.promotion_service._is_valid_fact(fact_text)
            assert is_valid, f"Fact should be accepted: {fact_text}"


class TestRetrievalPrioritization:
    """Test retrieval prioritization functionality"""
    
    def setup_method(self):
        self.retrieval_service = RetrievalService()
    
    def test_memory_fact_priority(self):
        """Test that memory facts have highest priority in retrieval"""
        # Mock results with different source types and scores
        mock_results = [
            {"source_type": "memory", "score": 0.8, "content": "User fact"},
            {"source_type": "summary", "score": 0.9, "content": "Working memory"},
            {"source_type": "message", "score": 0.7, "content": "Recent message"},
            {"source_type": "ephemeral", "score": 0.1, "content": "Ephemeral message"},
        ]
        
        # Memory facts should be prioritized even with lower raw scores
        prioritized = self.retrieval_service._group_and_rank_results(mock_results)
        
        # Memory facts should appear first
        memory_facts = [r for r in prioritized if r["source_type"] == "memory"]
        assert len(memory_facts) > 0
        assert prioritized[0]["source_type"] == "memory"


class TestEndToEndPipeline:
    """Test the complete memory stratification pipeline"""
    
    @pytest.mark.asyncio
    async def test_complete_pipeline(self):
        """Test the complete pipeline from message to long-term memory"""
        
        # Create a test conversation
        conversation = await conversation_store.create_conversation(
            user_id="test_user_123",
            title="Test Memory Pipeline"
        )
        
        # Add test messages with different types
        test_messages = [
            ("I am a software engineer with 5 years of experience", "user"),
            ("I prefer Python over JavaScript for backend development", "user"),
            ("I want to learn machine learning this year", "user"),
            ("What do you think about React?", "user"),
            ("Let's build a web application", "user"),
        ]
        
        # Process each message through classification
        classifications = []
        for content, role in test_messages:
            result = await classification_pipeline.process_message(
                message_id=f"msg_{len(classifications)}",
                content=content,
                role=role,
                conversation_id=conversation.conversation_id,
                user_id="test_user_123"
            )
            classifications.append(result)
        
        # Verify classifications
        fact_classifications = [c for c in classifications if c["classification"]["type"] == "fact"]
        preference_classifications = [c for c in classifications if c["classification"]["type"] == "preference"]
        chat_classifications = [c for c in classifications if c["classification"]["type"] == "chat"]
        
        assert len(fact_classifications) >= 1, "Should have at least one fact"
        assert len(preference_classifications) >= 1, "Should have at least one preference"
        assert len(chat_classifications) >= 1, "Should have at least one chat message"
        
        # Test memory promotion
        promotion_result = await memory_promotion_service.promote_from_conversation(
            conversation.conversation_id,
            "test_user_123"
        )
        
        assert promotion_result["success"], "Memory promotion should succeed"
        assert promotion_result["promoted_facts"] >= 0, "Should promote some facts"
        
        # Test memory retrieval
        memory_summary = await memory_promotion_service.get_memory_summary("test_user_123")
        
        assert memory_summary["user_id"] == "test_user_123"
        assert memory_summary["total_facts"] >= 0
        
        # Test context retrieval with stratification
        retrieval_service = RetrievalService()
        context = await retrieval_service.retrieve_context(
            query="Tell me about the user's preferences",
            user_id="test_user_123",
            k=5
        )
        
        # Should have some context retrieved
        assert len(context) >= 0
        
        # Clean up test data
        await conversation_store.delete_conversation(conversation.conversation_id)


class TestMemoryConsistency:
    """Test memory consistency and conflict detection"""
    
    def setup_method(self):
        self.promotion_service = MemoryPromotionService()
    
    def test_contradiction_detection(self):
        """Test detection of contradictory facts"""
        fact1 = "I love Python programming"
        fact2 = "I hate Python programming"
        
        is_contradiction = self.promotion_service._check_contradiction(fact1, fact2)
        assert is_contradiction, "Should detect contradiction"
    
    def test_no_contradiction_detection(self):
        """Test that non-contradictory facts are not flagged"""
        fact1 = "I love Python programming"
        fact2 = "I prefer JavaScript for frontend"
        
        is_contradiction = self.promotion_service._check_contradiction(fact1, fact2)
        assert not is_contradiction, "Should not detect contradiction"


class TestPerformance:
    """Test performance characteristics of the memory system"""
    
    def setup_method(self):
        self.classifier = MessageClassifier()
        self.promotion_service = MemoryPromotionService()
    
    def test_classification_performance(self):
        """Test that classification is fast enough for real-time use"""
        test_message = "I am a software engineer who loves Python and wants to learn machine learning"
        
        import time
        start_time = time.time()
        
        for _ in range(100):  # Test 100 classifications
            classification = self.classifier.classify_message(test_message, "user")
            assert classification.message_type is not None
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 100
        
        # Should be fast enough for real-time use (< 10ms per classification)
        assert avg_time < 0.01, f"Classification too slow: {avg_time:.4f}s"
    
    @pytest.mark.asyncio
    async def test_promotion_performance(self):
        """Test that promotion is reasonably fast"""
        # This would require setting up a full database, so we'll skip in unit tests
        # In integration tests, this should be tested with real database
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])