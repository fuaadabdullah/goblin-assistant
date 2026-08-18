"""Deterministic tests for current memory stratification services."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from api.services.memory_promotion import MemoryPromotionService
from api.services.message_classifier import (
    MessageClassification,
    MessageClassifier,
    MessageType,
)


class TestMessageClassification:
    def setup_method(self) -> None:
        self.classifier = MessageClassifier()

    def test_fact_classification(self) -> None:
        classification = self.classifier.classify_message(
            "I am a software engineer with 5 years of experience", "user"
        )
        assert classification.message_type == MessageType.FACT
        assert classification.confidence > 0.5

    def test_preference_classification(self) -> None:
        classification = self.classifier.classify_message("I prefer Python over JavaScript", "user")
        assert classification.message_type == MessageType.PREFERENCE
        assert classification.confidence > 0.5

    def test_chat_classification(self) -> None:
        classification = self.classifier.classify_message("The weather is nice today.", "user")
        assert classification.message_type == MessageType.CHAT

    def test_system_classification(self) -> None:
        classification = self.classifier.classify_message("System message", "system")
        assert classification.message_type == MessageType.SYSTEM
        assert classification.confidence == 1.0


@pytest.mark.asyncio
async def test_promotion_from_summary_evaluates_candidates() -> None:
    service = MemoryPromotionService()

    fake_classification = MessageClassification(
        message_type=MessageType.FACT,
        confidence=0.9,
        keywords=["python"],
        reasoning="fact",
    )

    with (
        patch("api.services.memory_promotion._service.extract_memory_candidates") as extract,
        patch.object(service, "evaluate_promotion_candidate", new=AsyncMock()) as evaluate,
    ):
        extract.return_value = [fake_classification, fake_classification]
        evaluate.return_value = {"promoted": False}
        results = await service.promote_from_summary("summary", "conv-1", "user-1")

    assert len(results) == 2
    assert evaluate.await_count == 2
