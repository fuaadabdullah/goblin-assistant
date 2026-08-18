"""Assistant tool skills package.

Import every skill module at package load time so tool registration side
effects populate the canonical registry for contract tests and runtime use.
"""

from __future__ import annotations

import importlib

_SKILL_MODULES = (
    # Core assistant contract surface
    "memory_recall",
    "file_tool",
    "project_tool",
    "task_tool",
    "git_tool",
    "github_tool",
    "web_search",
    "academic_search",
    "citation_graph",
    "research_tool",
    # Sandbox / terminal
    "sandbox_tool",
    "terminal_tool",
    # Financial skill surface
    "market_data",
    "dcf_calculator",
    "portfolio_analyzer",
    "earnings_summarizer",
    "stock_screener",
    # Additional skills from main
    "news_summarizer",
    "sec_filings",
)


def _import_selected_skills() -> None:
    package_name = __name__
    for module_name in _SKILL_MODULES:
        try:
            importlib.import_module(f"{package_name}.{module_name}")
        except ModuleNotFoundError:
            pass


_import_selected_skills()
