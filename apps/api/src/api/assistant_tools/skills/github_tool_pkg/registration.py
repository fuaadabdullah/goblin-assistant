from __future__ import annotations

from typing import Any, List, Optional

from ...registry import ToolDefinition, ToolParameter, register_tool
from .handlers import (
    handle_github_add_comment,
    handle_github_create_issue,
    handle_github_create_pr,
    handle_github_get_file,
    handle_github_get_issue,
    handle_github_get_pr,
    handle_github_get_repo,
    handle_github_list_issues,
    handle_github_list_prs,
    handle_github_list_repos,
    handle_github_search_code,
)


def _param(
    name: str,
    type_: str,
    description: str,
    *,
    required: bool = True,
    default: Optional[Any] = None,
    enum: Optional[List[str]] = None,
) -> ToolParameter:
    return ToolParameter(
        name=name,
        type=type_,
        description=description,
        required=required,
        default=default,
        enum=enum,
    )


def register_github_tools() -> None:
    register_tool(
        ToolDefinition(
            name="github_get_repo",
            description=(
                "Use when the user wants details about a GitHub repository: "
                "description, stars, forks, open issues, language, topics, "
                "and default branch."
            ),
            parameters=[
                _param("owner", "string", "Repository owner (user or org name)."),
                _param("repo", "string", "Repository name."),
            ],
            handler=handle_github_get_repo,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_list_repos",
            description=(
                "Use when the user wants to list repositories for a GitHub "
                "user or organization, sorted by most recently updated."
            ),
            parameters=[
                _param("owner", "string", "GitHub username or organization name."),
                _param(
                    "owner_type",
                    "string",
                    "'user' or 'org'. Defaults to 'user'.",
                    required=False,
                    default="user",
                    enum=["user", "org"],
                ),
                _param(
                    "limit",
                    "integer",
                    "Max repos to return (up to 100). Default 30.",
                    required=False,
                    default=30,
                ),
            ],
            handler=handle_github_list_repos,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_list_issues",
            description=(
                "Use when the user wants to list issues in a GitHub "
                "repository. Excludes pull requests. Filter by state "
                "(open/closed/all)."
            ),
            parameters=[
                _param("owner", "string", "Repository owner."),
                _param("repo", "string", "Repository name."),
                _param(
                    "state",
                    "string",
                    "Issue state filter: open, closed, all.",
                    required=False,
                    default="open",
                    enum=["open", "closed", "all"],
                ),
                _param(
                    "limit",
                    "integer",
                    "Max issues to return. Default 20.",
                    required=False,
                    default=20,
                ),
            ],
            handler=handle_github_list_issues,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_get_issue",
            description=(
                "Use when the user wants to read a specific issue — its "
                "title, body, labels, assignees, and comment count."
            ),
            parameters=[
                _param("owner", "string", "Repository owner."),
                _param("repo", "string", "Repository name."),
                _param("number", "integer", "Issue number."),
            ],
            handler=handle_github_get_issue,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_create_issue",
            description=(
                "Use when the user wants to open a new issue in a GitHub "
                "repository. Returns the new issue number and URL. Requires "
                "GITHUB_TOKEN with repo write access."
            ),
            parameters=[
                _param("owner", "string", "Repository owner."),
                _param("repo", "string", "Repository name."),
                _param("title", "string", "Issue title."),
                _param(
                    "body",
                    "string",
                    "Issue description (markdown supported).",
                    required=False,
                ),
                _param(
                    "labels",
                    "array",
                    "List of label names to apply.",
                    required=False,
                ),
            ],
            handler=handle_github_create_issue,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_add_comment",
            description=(
                "Use when the user wants to add a comment to an existing "
                "issue or pull request. Works with both issues and PRs since "
                "they share the same comment endpoint."
            ),
            parameters=[
                _param("owner", "string", "Repository owner."),
                _param("repo", "string", "Repository name."),
                _param("number", "integer", "Issue or pull request number."),
                _param("body", "string", "Comment text (markdown supported)."),
            ],
            handler=handle_github_add_comment,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_list_prs",
            description=(
                "Use when the user wants to list pull requests in a GitHub "
                "repository. Filter by state: open, closed, or all."
            ),
            parameters=[
                _param("owner", "string", "Repository owner."),
                _param("repo", "string", "Repository name."),
                _param(
                    "state",
                    "string",
                    "PR state: open, closed, all. Default open.",
                    required=False,
                    default="open",
                    enum=["open", "closed", "all"],
                ),
                _param(
                    "limit",
                    "integer",
                    "Max PRs to return. Default 20.",
                    required=False,
                    default=20,
                ),
            ],
            handler=handle_github_list_prs,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_get_pr",
            description=(
                "Use when the user wants to read a specific pull request — "
                "its title, body, diff stats, head/base branches, merge "
                "status, and whether it is a draft."
            ),
            parameters=[
                _param("owner", "string", "Repository owner."),
                _param("repo", "string", "Repository name."),
                _param("number", "integer", "Pull request number."),
            ],
            handler=handle_github_get_pr,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_create_pr",
            description=(
                "Use when the user wants to open a pull request. Requires "
                "GITHUB_TOKEN with repo write access. Specify the head branch "
                "(source) and base branch (target)."
            ),
            parameters=[
                _param("owner", "string", "Repository owner."),
                _param("repo", "string", "Repository name."),
                _param("title", "string", "Pull request title."),
                _param(
                    "head",
                    "string",
                    "Branch containing the changes (source branch).",
                ),
                _param(
                    "base",
                    "string",
                    "Branch to merge into (target branch, e.g. 'main').",
                ),
                _param(
                    "body",
                    "string",
                    "PR description (markdown supported).",
                    required=False,
                ),
            ],
            handler=handle_github_create_pr,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_get_file",
            description=(
                "Use when the user wants to read the contents of a specific "
                "file from a GitHub repository. Optionally specify a branch, "
                "tag, or commit SHA via ref."
            ),
            parameters=[
                _param("owner", "string", "Repository owner."),
                _param("repo", "string", "Repository name."),
                _param(
                    "path",
                    "string",
                    "File path within the repository, e.g. 'src/main.py'.",
                ),
                _param(
                    "ref",
                    "string",
                    "Branch name, tag, or commit SHA. Defaults to the repo's default branch.",
                    required=False,
                ),
            ],
            handler=handle_github_get_file,
            category="github",
        )
    )

    register_tool(
        ToolDefinition(
            name="github_search_code",
            description=(
                "Use when the user wants to search for code across GitHub "
                "repositories. Supports GitHub code search qualifiers like "
                "'repo:', 'language:', 'path:', etc. Requires GITHUB_TOKEN "
                "for best results."
            ),
            parameters=[
                _param(
                    "query",
                    "string",
                    "GitHub code search query, e.g. 'authenticate repo:octocat/hello-world language:python'.",
                ),
                _param(
                    "limit",
                    "integer",
                    "Max results to return (up to 30). Default 10.",
                    required=False,
                    default=10,
                ),
            ],
            handler=handle_github_search_code,
            category="github",
        )
    )


__all__ = ["register_github_tools"]
