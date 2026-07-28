from __future__ import annotations

from api.core.orchestration import (
    create_simple_orchestration_plan,
    parse_natural_language,
)


def test_parse_natural_language_uses_default_goblin_when_no_patterns():
    plan = parse_natural_language("Write release notes", default_goblin="docs-writer")

    assert plan.complexity == "low"
    assert plan.estimated_duration == 30
    assert len(plan.steps) == 1
    assert plan.steps[0].goblin == "docs-writer"
    assert plan.steps[0].task == "Write release notes"
    assert plan.steps[0].dependencies == []


def test_parse_natural_language_detects_search_analyze_and_create_pipeline():
    plan = parse_natural_language("Search, analyze, and create a report")

    assert [step.goblin for step in plan.steps] == [
        "search-goblin",
        "analyze-goblin",
        "create-goblin",
    ]
    assert plan.steps[0].dependencies == []
    assert plan.steps[1].dependencies == ["search-goblin"]
    assert plan.steps[2].dependencies == ["analyze-goblin"]
    assert plan.complexity == "medium"
    assert plan.estimated_duration == 90


def test_parse_natural_language_supports_single_analyze_or_create_branches():
    analyze_plan = parse_natural_language("Review this diff")
    create_plan = parse_natural_language("Generate a summary")

    assert len(analyze_plan.steps) == 1
    assert analyze_plan.steps[0].goblin == "analyze-goblin"
    assert analyze_plan.steps[0].dependencies == []

    assert len(create_plan.steps) == 1
    assert create_plan.steps[0].goblin == "create-goblin"
    assert create_plan.steps[0].dependencies == []


def test_parse_natural_language_truncates_fallback_task_text():
    text = "x" * 120
    plan = parse_natural_language(text)

    assert plan.steps[0].goblin == "general-goblin"
    assert plan.steps[0].task == ("x" * 100) + "..."


def test_create_simple_orchestration_plan_defaults_and_truncates():
    plan = create_simple_orchestration_plan("y" * 120)

    assert plan["total_batches"] == 1
    assert plan["max_parallel"] == 1
    assert plan["estimated_cost"] == 0.05
    assert plan["steps"][0]["id"] == "step1"
    assert plan["steps"][0]["goblin"] == "docs-writer"
    assert plan["steps"][0]["task"] == ("y" * 100) + "..."
    assert plan["steps"][0]["dependencies"] == []


def test_create_simple_orchestration_plan_uses_explicit_default_goblin():
    plan = create_simple_orchestration_plan("Draft docs", default_goblin="general-goblin")

    assert plan["steps"][0]["goblin"] == "general-goblin"
    assert plan["steps"][0]["task"] == "Draft docs"
