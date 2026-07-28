from __future__ import annotations

from api.routing.prompt_classifier import prompt_classifier
from api.services.smart_router_pkg.types import TaskType


def test_prompt_classifier_handles_typo_summarization():
    result = prompt_classifier.classify("Summrize this arcticle about climate change")

    assert result == TaskType.SUMMARIZATION.value


def test_prompt_classifier_returns_label_string():
    result = prompt_classifier.classify("Write a Python script")

    assert result == TaskType.CODE_GENERATION.value
    assert isinstance(result, str)
