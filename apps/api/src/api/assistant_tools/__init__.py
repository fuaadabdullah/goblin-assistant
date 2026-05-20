"""Tool system for Goblin Assistant financial skills."""

# Import skills to trigger tool registration at module load time.
from . import skills  # noqa: F401
from .skills import market_data  # noqa: F401
from .skills import dcf_calculator  # noqa: F401
from .skills import portfolio_analyzer  # noqa: F401
from .skills import earnings_summarizer  # noqa: F401
from .skills import stock_screener  # noqa: F401
