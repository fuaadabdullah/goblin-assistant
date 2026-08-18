"""Tool system for Goblin Assistant financial skills.

assistant_tools is the canonical tool system.
"""

# Import skills to trigger tool registration at module load time.
from . import skills  # noqa: F401
from .skills import (
    academic_search,  # noqa: F401  # imported for tool registration
    citation_graph,  # noqa: F401  # imported for tool registration
    dcf_calculator,  # noqa: F401  # imported for tool registration
    earnings_summarizer,  # noqa: F401  # imported for tool registration
    file_tool,  # noqa: F401  # imported for tool registration
    git_tool,  # noqa: F401  # imported for tool registration
    github_tool,  # noqa: F401  # imported for tool registration
    market_data,  # noqa: F401  # imported for tool registration
    memory_recall,  # noqa: F401  # imported for tool registration
    news_summarizer,  # noqa: F401  # imported for tool registration
    portfolio_analyzer,  # noqa: F401  # imported for tool registration
    project_tool,  # noqa: F401  # imported for tool registration
    research_tool,  # noqa: F401  # imported for tool registration
    sandbox_tool,  # noqa: F401  # imported for tool registration
    sec_filings,  # noqa: F401  # imported for tool registration
    stock_screener,  # noqa: F401  # imported for tool registration
    task_tool,  # noqa: F401  # imported for tool registration
    terminal_tool,  # noqa: F401  # imported for tool registration
    web_search,  # noqa: F401  # imported for tool registration
)
