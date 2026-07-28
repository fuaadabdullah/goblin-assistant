from __future__ import annotations

from api.pipeline.tool_selection import ToolSelectionModel
from api.routing.intent_classifier import IntentLabel, IntentResult


def test_research_intent_selects_web_research_tools():
    model = ToolSelectionModel()

    selected = model.select(
        IntentResult(label=IntentLabel.RESEARCH, confidence=0.92, method="keyword")
    )

    assert "web_search" in selected
    assert "lightweight_research" in selected


def test_finance_intent_selects_web_tools_for_live_data():
    model = ToolSelectionModel()

    selected = model.select(
        IntentResult(label=IntentLabel.FINANCE, confidence=0.9, method="keyword")
    )

    assert "web_search" in selected
