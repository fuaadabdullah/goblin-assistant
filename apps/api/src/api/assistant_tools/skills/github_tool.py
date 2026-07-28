"""
GitHub tools for Goblin Assistant.

Compatibility facade that preserves historical symbols while delegating
implementation to github_tool_pkg modules.
"""

from __future__ import annotations

from .github_tool_pkg.client import _BASE, _TIMEOUT
from .github_tool_pkg.client import get as _get
from .github_tool_pkg.client import headers as _headers
from .github_tool_pkg.client import post as _post
from .github_tool_pkg.handlers import (
    handle_github_add_comment as _handle_github_add_comment,
)
from .github_tool_pkg.handlers import (
    handle_github_create_issue as _handle_github_create_issue,
)
from .github_tool_pkg.handlers import (
    handle_github_create_pr as _handle_github_create_pr,
)
from .github_tool_pkg.handlers import (
    handle_github_get_file as _handle_github_get_file,
)
from .github_tool_pkg.handlers import (
    handle_github_get_issue as _handle_github_get_issue,
)
from .github_tool_pkg.handlers import (
    handle_github_get_pr as _handle_github_get_pr,
)
from .github_tool_pkg.handlers import (
    handle_github_get_repo as _handle_github_get_repo,
)
from .github_tool_pkg.handlers import (
    handle_github_list_issues as _handle_github_list_issues,
)
from .github_tool_pkg.handlers import (
    handle_github_list_prs as _handle_github_list_prs,
)
from .github_tool_pkg.handlers import (
    handle_github_list_repos as _handle_github_list_repos,
)
from .github_tool_pkg.handlers import (
    handle_github_search_code as _handle_github_search_code,
)
from .github_tool_pkg.registration import register_github_tools

register_github_tools()

__all__ = [
    "_BASE",
    "_TIMEOUT",
    "_get",
    "_headers",
    "_post",
    "_handle_github_add_comment",
    "_handle_github_create_issue",
    "_handle_github_create_pr",
    "_handle_github_get_file",
    "_handle_github_get_issue",
    "_handle_github_get_pr",
    "_handle_github_get_repo",
    "_handle_github_list_issues",
    "_handle_github_list_prs",
    "_handle_github_list_repos",
    "_handle_github_search_code",
    "register_github_tools",
]
