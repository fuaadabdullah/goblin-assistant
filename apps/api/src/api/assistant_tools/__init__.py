"""Tool system for Goblin Assistant financial skills."""

# Import skills to trigger tool registration at module load time.
from . import skills  # noqa: F401
from .skills import dcf_calculator  # noqa: F401
from .skills import earnings_summarizer  # noqa: F401
from .skills import file_tool  # noqa: F401
from .skills import git_tool  # noqa: F401
from .skills import github_tool  # noqa: F401
from .skills import market_data  # noqa: F401
from .skills import portfolio_analyzer  # noqa: F401
from .skills import project_tool  # noqa: F401
from .skills import research_tool  # noqa: F401
from .skills import sec_filings  # noqa: F401
from .skills import stock_screener  # noqa: F401
from .skills import task_tool  # noqa: F401
