from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from api.departments.models import DepartmentId, DepartmentSelection
from api.pipeline.context import DecisionContext, RequestContext
from api.pipeline.pipeline import RequestPipeline
from api.routing.provider_selection import ProviderScore


def test_provider_selection_enters_staged_router_from_raw_prompt():
    provider_selection = MagicMock()
    provider_selection.score_prompt.return_value = [
        ProviderScore(provider_id="openai", score=0.9, pct=90),
        ProviderScore(provider_id="anthropic", score=0.7, pct=10),
    ]
    pipeline = RequestPipeline(
        intent_classifier=MagicMock(),
        context_assembly_service=MagicMock(),
        smart_router=MagicMock(),
        tool_selection_model=MagicMock(),
    )
    request = RequestContext(
        user_id="user-1",
        conversation_id="conversation-1",
        raw_message="raw prompt",
        sanitized_message="Please refactor this class",
    )
    decision = DecisionContext(
        intent=SimpleNamespace(label=SimpleNamespace(value="coding"), confidence=0.91),
        task_type="coding",
    )
    department_selection = DepartmentSelection(
        department_id=DepartmentId.CODING,
        resolved_provider="anthropic",
        resolved_model="claude-sonnet-4-20250514",
        fallback_chain=["openai"],
    )
    history = [{"role": "user", "content": "previous"}]

    with patch("api.routing.provider_selection.provider_selection_model", provider_selection):
        scored = pipeline._run_provider_selection(
            request,
            decision,
            history,
            department_selection,
            routing_id="live-route-1",
        )

    assert [score.provider_id for score in scored] == ["openai", "anthropic"]
    provider_selection.score_prompt.assert_called_once()
    args, kwargs = provider_selection.score_prompt.call_args
    assert args[0][0] == "anthropic"
    assert args[1] == "Please refactor this class"
    assert kwargs["task_type"] == "coding"
    assert kwargs["conversation_history"] == history
    assert kwargs["intent_label"] == "coding"
    assert kwargs["intent_confidence"] == 0.91
    assert kwargs["routing_id"] == "live-route-1"
    assert kwargs["prefer_supplied_task_type"] is True
    assert scored[0].model_name == "gpt-4o"
