"""Tool system for Goblin Assistant financial skills.

assistant_tools is the canonical tool system.
"""

# Import skills to trigger tool registration at module load time.
from . import skills  # noqa: F401
from .skills import (
    academic_search,  # noqa: F401
    citation_graph,  # noqa: F401
    dcf_calculator,  # noqa: F401
    earnings_summarizer,  # noqa: F401
    file_tool,  # noqa: F401
    git_tool,  # noqa: F401
    github_tool,  # noqa: F401
    market_data,  # noqa: F401
    memory_recall,  # noqa: F401
    news_summarizer,  # noqa: F401
    portfolio_analyzer,  # noqa: F401
    project_tool,  # noqa: F401
    research_tool,  # noqa: F401
    sandbox_tool,  # noqa: F401
    sec_filings,  # noqa: F401
    stock_screener,  # noqa: F401
    task_tool,  # noqa: F401
    terminal_tool,  # noqa: F401
    web_search,  # noqa: F401
)
