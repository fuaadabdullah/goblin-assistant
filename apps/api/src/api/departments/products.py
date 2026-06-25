"""Product-facing labels layered on top of the internal department taxonomy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .models import DepartmentId


@dataclass(frozen=True)
class ProductExperience:
    product_id: str
    display_name: str
    department_id: DepartmentId
    description: str
    surface_title: str
    surface_body: str
    starter_prompt: str
    icon: str
    featured: bool = True


_PRODUCTS: Dict[str, ProductExperience] = {
    "research": ProductExperience(
        product_id="research",
        display_name="Research Goblin",
        department_id=DepartmentId.RESEARCH,
        description="Turns open questions into sourced briefs, summaries, and deep dives.",
        surface_title="Research briefs",
        surface_body="Turn a topic into citations, synthesis, and next-step follow-ups.",
        starter_prompt=(
            "Create a concise research brief on the current state of AI regulation in the US "
            "with sources."
        ),
        icon="🔎",
    ),
    "coding": ProductExperience(
        product_id="coding",
        display_name="Coding Goblin",
        department_id=DepartmentId.CODING,
        description="Ships code, fixes bugs, and tightens implementation details.",
        surface_title="Code delivery",
        surface_body="Debug, refactor, review, and ship with fewer dead ends.",
        starter_prompt="Debug this Python code and show me the fix with a brief explanation.",
        icon="⚙️",
    ),
    "finance": ProductExperience(
        product_id="finance",
        display_name="Finance Goblin",
        department_id=DepartmentId.REASONING,
        description="Handles valuation, analysis, and decision support for money questions.",
        surface_title="Finance analysis",
        surface_body="Model the tradeoffs, compare scenarios, and flag the risks.",
        starter_prompt=(
            "Analyze AAPL earnings, valuation, and analyst sentiment. Keep it concise and "
            "decision-ready."
        ),
        icon="📈",
    ),
    "strategy": ProductExperience(
        product_id="strategy",
        display_name="Strategy Goblin",
        department_id=DepartmentId.REASONING,
        description="Turns messy goals into plans, tradeoffs, and priorities.",
        surface_title="Strategy notes",
        surface_body="Break the objective into options, constraints, and a recommended path.",
        starter_prompt=(
            "Build a strategy memo for launching a new AI feature next quarter. Focus on "
            "tradeoffs and risks."
        ),
        icon="🎯",
    ),
    "operations": ProductExperience(
        product_id="operations",
        display_name="Operations Goblin",
        department_id=DepartmentId.TOOL_USE,
        description="Builds repeatable workflows, structured actions, and execution plans.",
        surface_title="Operations flow",
        surface_body="Automate the repeatable stuff and keep the process moving.",
        starter_prompt=(
            "Design an operations workflow for handling customer escalations from intake to "
            "resolution."
        ),
        icon="🧩",
    ),
    "general": ProductExperience(
        product_id="general",
        display_name="General Goblin",
        department_id=DepartmentId.GENERAL,
        description="Handles broad requests that do not need a narrower product experience.",
        surface_title="General help",
        surface_body="Use this when the request spans several outcomes or needs a broad first pass.",
        starter_prompt="Help me think through a complex request and suggest the best next step.",
        icon="✨",
        featured=False,
    ),
}


def get_product_info(product_id: str) -> Optional[ProductExperience]:
    """Return the product experience for a public product id."""
    return _PRODUCTS.get(product_id.strip().lower()) if product_id else None


def list_products() -> List[ProductExperience]:
    """Return all product experiences in display order."""
    return list(_PRODUCTS.values())


def list_featured_products() -> List[ProductExperience]:
    """Return the product experiences shown in the public UI."""
    return [product for product in _PRODUCTS.values() if product.featured]


def resolve_department_for_product(product_id: str) -> DepartmentId:
    """Map a product id to its internal department id."""
    product = get_product_info(product_id)
    if product is None:
        raise KeyError(f"Unknown product '{product_id}'")
    return product.department_id
