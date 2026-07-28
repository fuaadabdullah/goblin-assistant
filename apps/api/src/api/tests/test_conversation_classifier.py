from __future__ import annotations

from api.services.conversation_classifier import ConversationCategory, conversation_classifier


def test_conversation_classifier_handles_typo_research_signal():
    result = conversation_classifier.classify(
        "Can you reseach the latets current developments in AI policy?"
    )

    assert result == ConversationCategory.RESEARCH.value


def test_conversation_classifier_treats_live_questions_as_research():
    result = conversation_classifier.classify("What is the latest on AI policy?")

    assert result == ConversationCategory.RESEARCH.value
