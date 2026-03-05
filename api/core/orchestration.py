"""
Shared orchestration logic for parsing natural language and creating execution plans.
Consolidated from parse_router.py and api_router.py to eliminate duplication.
"""

from typing import Optional, List
from pydantic import BaseModel


class OrchestrationStep(BaseModel):
    goblin: str
    task: str
    dependencies: List[str] = []


class OrchestrationPlan(BaseModel):
    steps: List[OrchestrationStep]
    estimated_duration: int = 0
    complexity: str = "medium"


def parse_natural_language(
    text: str, default_goblin: Optional[str] = None
) -> OrchestrationPlan:
    """
    Parse natural language text into an orchestration plan using keyword-based pattern matching.

    Args:
        text: The natural language text to parse
        default_goblin: Default goblin to use if no patterns are detected

    Returns:
        OrchestrationPlan with parsed steps, duration estimate, and complexity rating
    """
    text_lower = text.lower()

    # Simple keyword-based parsing (in production, use NLP/AI)
    steps = []

    # Detect common patterns
    if "search" in text_lower or "find" in text_lower or "query" in text_lower:
        steps.append(
            OrchestrationStep(
                goblin="search-goblin",
                task="Search for information",
                dependencies=[],
            )
        )

    if "analyze" in text_lower or "review" in text_lower or "examine" in text_lower:
        steps.append(
            OrchestrationStep(
                goblin="analyze-goblin",
                task="Analyze the results",
                dependencies=["search-goblin"] if steps else [],
            )
        )

    if "create" in text_lower or "build" in text_lower or "generate" in text_lower:
        steps.append(
            OrchestrationStep(
                goblin="create-goblin",
                task="Create or generate content",
                dependencies=["analyze-goblin"] if len(steps) > 1 else [],
            )
        )

    # If no specific patterns detected, use default goblin
    if not steps:
        default_goblin = default_goblin or "general-goblin"
        steps.append(
            OrchestrationStep(
                goblin=default_goblin,
                task=text[:100] + "..." if len(text) > 100 else text,
                dependencies=[],
            )
        )

    # Estimate complexity and duration
    complexity = "low" if len(steps) <= 1 else "medium" if len(steps) <= 3 else "high"
    duration = len(steps) * 30  # 30 seconds per step estimate

    return OrchestrationPlan(
        steps=steps, estimated_duration=duration, complexity=complexity
    )


def create_simple_orchestration_plan(
    text: str, default_goblin: Optional[str] = None
) -> dict:
    """
    Create a simple orchestration plan with a single step.
    Used for basic orchestration requests that don't need complex multi-step parsing.

    Args:
        text: The task description
        default_goblin: Default goblin to assign the task to

    Returns:
        Dictionary with orchestration plan in the format expected by api_router
    """
    goblin = default_goblin or "docs-writer"
    task = text[:100] + "..." if len(text) > 100 else text

    return {
        "steps": [
            {
                "id": "step1",
                "goblin": goblin,
                "task": task,
                "dependencies": [],
                "batch": 0,
            }
        ],
        "total_batches": 1,
        "max_parallel": 1,
        "estimated_cost": 0.05,
    }
