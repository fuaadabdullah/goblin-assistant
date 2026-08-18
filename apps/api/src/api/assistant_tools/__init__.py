"""Tool system for Goblin Assistant financial skills.

assistant_tools is the canonical tool system.
"""

# Import skills to trigger tool registration at module load time.
from . import skills
from .skills import (
    academic_search,
    citation_graph,
    dcf_calculator,
    earnings_summarizer,
    file_tool,
    git_tool,
    github_tool,
    market_data,
    memory_recall,
    news_summarizer,
    portfolio_analyzer,
    project_tool,
    research_tool,
    sandbox_tool,
    sec_filings,
    stock_screener,
    task_tool,
    terminal_tool,
    web_search,
)

__all__ = [
    "academic_search",
    "citation_graph",
    "dcf_calculator",
    "earnings_summarizer",
    "file_tool",
    "git_tool",
    "github_tool",
    "market_data",
    "memory_recall",
    "news_summarizer",
    "portfolio_analyzer",
    "project_tool",
    "research_tool",
    "sandbox_tool",
    "sec_filings",
    "skills",
    "stock_screener",
    "task_tool",
    "terminal_tool",
    "web_search",
]
