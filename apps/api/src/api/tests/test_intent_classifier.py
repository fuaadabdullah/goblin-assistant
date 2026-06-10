"""Unit tests for the IntentClassifier."""

import pytest

from api.routing.intent_classifier import (
    IntentClassifier,
    IntentLabel,
    IntentResult,
    map_intent_to_task_type,
)


@pytest.fixture
def classifier():
    return IntentClassifier()


# ---------------------------------------------------------------------------
# Keyword classification — each label
# ---------------------------------------------------------------------------


class TestKeywordClassification:
    def test_coding_from_function_request(self, classifier):
        result = classifier.classify("Write a function to parse JSON in Python")
        assert result.label == IntentLabel.CODING
        assert result.method == "keyword"
        assert result.confidence > 0

    def test_coding_from_debug_request(self, classifier):
        result = classifier.classify("I'm getting a TypeError in my TypeScript code")
        assert result.label == IntentLabel.CODING

    def test_coding_from_code_syntax(self, classifier):
        # ≥3 code-syntax tokens should trigger CODING
        prompt = "def foo():\n    return bar\n\nclass Baz:\n    def __init__(self): pass"
        result = classifier.classify(prompt)
        assert result.label == IntentLabel.CODING

    def test_research_from_literature(self, classifier):
        result = classifier.classify(
            "What does the literature say about transformer attention mechanisms?"
        )
        assert result.label == IntentLabel.RESEARCH

    def test_research_from_summarize_article(self, classifier):
        result = classifier.classify("Summarize this article about climate change")
        assert result.label == IntentLabel.RESEARCH

    def test_creative_from_story(self, classifier):
        result = classifier.classify("Write a short story about a robot learning to paint")
        assert result.label == IntentLabel.CREATIVE

    def test_creative_from_poem(self, classifier):
        result = classifier.classify("Write a poem about the ocean at night")
        assert result.label == IntentLabel.CREATIVE

    def test_business_from_pitch(self, classifier):
        result = classifier.classify("Help me write a pitch deck for our Series A raise")
        assert result.label == IntentLabel.BUSINESS

    def test_business_from_gtm(self, classifier):
        result = classifier.classify("What should our go-to-market strategy look like?")
        assert result.label == IntentLabel.BUSINESS

    def test_finance_from_portfolio(self, classifier):
        result = classifier.classify(
            "What is the Value at Risk of my portfolio given these positions?"
        )
        assert result.label == IntentLabel.FINANCE

    def test_finance_from_trading(self, classifier):
        result = classifier.classify("How do I backtest a mean-reversion trading strategy?")
        assert result.label == IntentLabel.FINANCE

    def test_reasoning_from_pros_cons(self, classifier):
        result = classifier.classify("What are the pros and cons of microservices vs monolith?")
        assert result.label == IntentLabel.REASONING

    def test_reasoning_from_step_by_step(self, classifier):
        result = classifier.classify("Think step by step through this problem")
        assert result.label == IntentLabel.REASONING

    def test_agent_task_from_automate(self, classifier):
        result = classifier.classify("Automate the process of sending weekly summary emails")
        assert result.label == IntentLabel.AGENT_TASK

    def test_agent_task_from_pipeline(self, classifier):
        result = classifier.classify(
            "Build a pipeline that fetches, transforms, and loads CSV files to PostgreSQL"
        )
        assert result.label == IntentLabel.AGENT_TASK

    def test_agent_task_from_deploy(self, classifier):
        result = classifier.classify("Deploy this Docker container to our staging environment")
        assert result.label == IntentLabel.AGENT_TASK


# ---------------------------------------------------------------------------
# Fallback and edge cases
# ---------------------------------------------------------------------------


class TestFallback:
    def test_empty_prompt_returns_research(self, classifier):
        result = classifier.classify("")
        assert result.label == IntentLabel.RESEARCH
        assert result.confidence < 0.5

    def test_generic_question_returns_result(self, classifier):
        result = classifier.classify("Hello, how are you?")
        assert isinstance(result.label, IntentLabel)
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_range(self, classifier):
        for prompt in [
            "Write a function in Python",
            "What is the Sharpe ratio?",
            "Tell me a story",
        ]:
            result = classifier.classify(prompt)
            assert 0.0 <= result.confidence <= 1.0

    def test_method_is_keyword(self, classifier):
        result = classifier.classify("Any prompt at all")
        assert result.method == "keyword"


# ---------------------------------------------------------------------------
# classify_messages
# ---------------------------------------------------------------------------


class TestClassifyMessages:
    def test_uses_last_user_message(self, classifier):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Write a Python function to sort a list"},
        ]
        result = classifier.classify_messages(messages)
        assert result.label == IntentLabel.CODING

    def test_empty_messages_returns_default(self, classifier):
        result = classifier.classify_messages([])
        assert result.label == IntentLabel.RESEARCH

    def test_no_user_messages_returns_default(self, classifier):
        messages = [{"role": "assistant", "content": "How can I help?"}]
        result = classifier.classify_messages(messages)
        assert result.label == IntentLabel.RESEARCH

    def test_multipart_content(self, classifier):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Write a story about the sea"},
                ],
            }
        ]
        result = classifier.classify_messages(messages)
        assert result.label == IntentLabel.CREATIVE


# ---------------------------------------------------------------------------
# IntentResult.to_dict
# ---------------------------------------------------------------------------


class TestIntentResultDict:
    def test_to_dict_shape(self, classifier):
        result = classifier.classify("Write a Python script")
        d = result.to_dict()
        assert "label" in d
        assert "confidence" in d
        assert "method" in d
        assert "runner_up" in d
        assert "runner_up_confidence" in d

    def test_label_is_string(self, classifier):
        result = classifier.classify("Deploy this service")
        d = result.to_dict()
        assert isinstance(d["label"], str)

    def test_runner_up_populated_for_strong_matches(self, classifier):
        # A highly specific prompt should produce a non-None runner_up
        result = classifier.classify(
            "Write a Python function and deploy it to production via CI/CD pipeline"
        )
        # Both CODING and AGENT_TASK should score — runner_up should be set
        d = result.to_dict()
        assert d["runner_up"] is not None or d["confidence"] > 0.5


# ---------------------------------------------------------------------------
# map_intent_to_task_type
# ---------------------------------------------------------------------------


class TestMapIntentToTaskType:
    def test_coding_maps_to_code(self):
        result = IntentResult(label=IntentLabel.CODING, confidence=0.9, method="keyword")
        assert map_intent_to_task_type(result) == "code"

    def test_research_maps_to_summary(self):
        result = IntentResult(label=IntentLabel.RESEARCH, confidence=0.8, method="keyword")
        assert map_intent_to_task_type(result) == "summary"

    def test_reasoning_maps_to_reasoning(self):
        result = IntentResult(label=IntentLabel.REASONING, confidence=0.8, method="keyword")
        assert map_intent_to_task_type(result) == "reasoning"

    def test_finance_maps_to_reasoning(self):
        result = IntentResult(label=IntentLabel.FINANCE, confidence=0.85, method="keyword")
        assert map_intent_to_task_type(result) == "reasoning"

    def test_creative_maps_to_none(self):
        result = IntentResult(label=IntentLabel.CREATIVE, confidence=0.9, method="keyword")
        assert map_intent_to_task_type(result) is None

    def test_agent_task_maps_to_none(self):
        result = IntentResult(label=IntentLabel.AGENT_TASK, confidence=0.9, method="keyword")
        assert map_intent_to_task_type(result) is None


# ---------------------------------------------------------------------------
# No prototypes → keyword-only mode
# ---------------------------------------------------------------------------


class TestNoPrototypes:
    def test_has_prototypes_false_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "api.routing.intent_classifier._PROTOTYPES_PATH",
            str(tmp_path / "nonexistent.json"),
        )
        c = IntentClassifier()
        assert c.has_prototypes() is False

    @pytest.mark.asyncio
    async def test_vectorized_falls_back_to_keyword_without_prototypes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "api.routing.intent_classifier._PROTOTYPES_PATH",
            str(tmp_path / "nonexistent.json"),
        )
        c = IntentClassifier()

        async def fake_embed(text: str):
            return [0.1] * 384

        result = await c.classify_vectorized("Write a Python function", fake_embed)
        assert result.method == "keyword"
        assert result.label == IntentLabel.CODING
