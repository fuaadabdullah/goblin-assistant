"""
Git tools for Goblin Assistant.

Registers tools for common git operations. Each tool runs git as a
subprocess in the configured repository directory.

Repo path resolution order:
  1. `repo_path` argument passed by the LLM (if provided)
  2. GOBLIN_GIT_REPO environment variable
  3. GOBLIN_FILE_WORKSPACE environment variable
  4. ~/goblin-workspace (hard default)

Destructive operations (force-push, reset --hard) are intentionally
excluded.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..registry import ToolDefinition, ToolParameter, register_tool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_repo() -> str:
    """Return the default repo path from env vars."""
    return os.environ.get(
        "GOBLIN_GIT_REPO",
        os.environ.get("GOBLIN_FILE_WORKSPACE", "~/goblin-workspace"),
    )


def _resolve_repo(repo_path: Optional[str]) -> Path:
    """Resolve and validate the repository directory."""
    raw = repo_path if repo_path else _default_repo()
    resolved = Path(raw).expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"Repository path does not exist: {raw}")
    if not resolved.is_dir():
        raise ValueError(f"Repository path is not a directory: {raw}")
    return resolved


def _run_git(args: List[str], cwd: Path) -> Dict[str, Any]:
    """Run a git command and return stdout/stderr as a dict."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
    )
    output = {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
        "repo": str(cwd),
    }
    if result.returncode != 0:
        output["error"] = result.stderr.strip() or result.stdout.strip()
    return output


# ---------------------------------------------------------------------------
# git_status
# ---------------------------------------------------------------------------


async def _handle_git_status(
    repo_path: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}
        return _run_git(["status", "--short", "--branch"], repo)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_status",
        description=(
            "Use when the user wants to see the current state of a git "
            "repository — which files are modified, staged, or untracked, "
            "and what branch is checked out. Runs 'git status --short'."
        ),
        parameters=[
            ToolParameter(
                name="repo_path",
                type="string",
                description=(
                    "Absolute path to the git repository. Defaults to the "
                    "GOBLIN_GIT_REPO environment variable or the goblin "
                    "workspace."
                ),
                required=False,
            ),
        ],
        handler=_handle_git_status,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_diff
# ---------------------------------------------------------------------------


async def _handle_git_diff(
    repo_path: Optional[str] = None,
    staged: bool = False,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}
        args = ["diff"]
        if staged:
            args.append("--staged")
        if path:
            args += ["--", path]
        return _run_git(args, repo)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_diff",
        description=(
            "Use when the user wants to see what changed in a repository. "
            "Shows unstaged changes by default; set staged=true to see "
            "staged (index) changes. Optionally narrow to a specific file "
            "path."
        ),
        parameters=[
            ToolParameter(
                name="repo_path",
                type="string",
                description="Absolute path to the git repository.",
                required=False,
            ),
            ToolParameter(
                name="staged",
                type="boolean",
                description=(
                    "If true, show staged (--cached) diff instead of "
                    "unstaged diff. Defaults to false."
                ),
                required=False,
                default=False,
            ),
            ToolParameter(
                name="path",
                type="string",
                description=("Limit the diff to this file or directory path."),
                required=False,
            ),
        ],
        handler=_handle_git_diff,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_log
# ---------------------------------------------------------------------------


async def _handle_git_log(
    repo_path: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}
        return _run_git(["log", "--oneline", f"-{max(1, limit)}"], repo)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_log",
        description=(
            "Use when the user wants to see the commit history of a "
            "repository. Returns one line per commit showing the short "
            "hash and subject."
        ),
        parameters=[
            ToolParameter(
                name="repo_path",
                type="string",
                description="Absolute path to the git repository.",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description=("Number of recent commits to show. Defaults to 20."),
                required=False,
                default=20,
            ),
        ],
        handler=_handle_git_log,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_add
# ---------------------------------------------------------------------------


async def _handle_git_add(
    paths: List[str],
    repo_path: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}
        if not paths:
            return {"error": "No paths specified. Pass ['.'] to stage all."}
        return _run_git(["add"] + paths, repo)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_add",
        description=(
            "Use when the user wants to stage files for a commit. Pass "
            "['.'] to stage all changes, or a list of specific file paths."
        ),
        parameters=[
            ToolParameter(
                name="paths",
                type="array",
                description=(
                    "List of file paths to stage, relative to the repo "
                    "root. Use ['.'] to stage everything."
                ),
            ),
            ToolParameter(
                name="repo_path",
                type="string",
                description="Absolute path to the git repository.",
                required=False,
            ),
        ],
        handler=_handle_git_add,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_commit
# ---------------------------------------------------------------------------


async def _handle_git_commit(
    message: str,
    repo_path: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}
        if not message.strip():
            return {"error": "Commit message cannot be empty."}
        return _run_git(["commit", "-m", message], repo)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_commit",
        description=(
            "Use when the user wants to commit staged changes. Requires "
            "files to already be staged with git_add. Runs "
            "'git commit -m <message>'."
        ),
        parameters=[
            ToolParameter(
                name="message",
                type="string",
                description="The commit message.",
            ),
            ToolParameter(
                name="repo_path",
                type="string",
                description="Absolute path to the git repository.",
                required=False,
            ),
        ],
        handler=_handle_git_commit,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_branch
# ---------------------------------------------------------------------------


async def _handle_git_branch(
    action: str,
    name: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}

        if action == "list":
            return _run_git(["branch", "-a"], repo)
        elif action == "create":
            if not name:
                return {"error": "name is required for action=create"}
            return _run_git(["branch", name], repo)
        elif action == "delete":
            if not name:
                return {"error": "name is required for action=delete"}
            return _run_git(["branch", "-d", name], repo)
        else:
            return {"error": (f"Unknown action '{action}'. Use: list, create, delete.")}

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_branch",
        description=(
            "Use when the user wants to list, create, or delete branches "
            "in a git repository. Use action='list' to see all branches, "
            "'create' to make a new branch, or 'delete' to remove one."
        ),
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="One of: list, create, delete.",
                enum=["list", "create", "delete"],
            ),
            ToolParameter(
                name="name",
                type="string",
                description=("Branch name. Required for create and delete actions."),
                required=False,
            ),
            ToolParameter(
                name="repo_path",
                type="string",
                description="Absolute path to the git repository.",
                required=False,
            ),
        ],
        handler=_handle_git_branch,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_checkout
# ---------------------------------------------------------------------------


async def _handle_git_checkout(
    target: str,
    repo_path: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}
        return _run_git(["checkout", target], repo)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_checkout",
        description=(
            "Use when the user wants to switch to a different branch or "
            "restore a file to its last committed state. Pass a branch "
            "name to switch branches, or a file path to discard local "
            "changes to that file."
        ),
        parameters=[
            ToolParameter(
                name="target",
                type="string",
                description=("Branch name to switch to, or file path to restore."),
            ),
            ToolParameter(
                name="repo_path",
                type="string",
                description="Absolute path to the git repository.",
                required=False,
            ),
        ],
        handler=_handle_git_checkout,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_pull
# ---------------------------------------------------------------------------


async def _handle_git_pull(
    repo_path: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}
        return _run_git(["pull"], repo)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_pull",
        description=(
            "Use when the user wants to fetch and merge changes from the "
            "remote into the current branch. Runs 'git pull'."
        ),
        parameters=[
            ToolParameter(
                name="repo_path",
                type="string",
                description="Absolute path to the git repository.",
                required=False,
            ),
        ],
        handler=_handle_git_pull,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_push
# ---------------------------------------------------------------------------


async def _handle_git_push(
    repo_path: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        try:
            repo = _resolve_repo(repo_path)
        except ValueError as exc:
            return {"error": str(exc)}
        return _run_git(["push"], repo)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_push",
        description=(
            "Use when the user wants to push local commits to the remote "
            "repository. Runs 'git push' on the current branch."
        ),
        parameters=[
            ToolParameter(
                name="repo_path",
                type="string",
                description="Absolute path to the git repository.",
                required=False,
            ),
        ],
        handler=_handle_git_push,
        category="git",
    )
)


# ---------------------------------------------------------------------------
# git_clone
# ---------------------------------------------------------------------------


async def _handle_git_clone(
    url: str,
    dest: Optional[str] = None,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        workspace = (
            Path(os.environ.get("GOBLIN_FILE_WORKSPACE", "~/goblin-workspace"))
            .expanduser()
            .resolve()
        )

        if dest:
            target = (workspace / dest).resolve()
            # Sandbox: destination must stay within workspace
            if workspace not in target.parents and target != workspace:
                return {"error": (f"Destination '{dest}' resolves outside the goblin workspace.")}
        else:
            # Default: clone into workspace root (git picks folder name)
            target = workspace

        target.mkdir(parents=True, exist_ok=True)
        args = ["clone", url]
        if dest:
            args.append(str(target))
        return _run_git(args, target.parent if dest else workspace)

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="git_clone",
        description=(
            "Use when the user wants to clone a remote git repository. "
            "Clones into the goblin workspace directory. Optionally "
            "specify a destination folder name within the workspace."
        ),
        parameters=[
            ToolParameter(
                name="url",
                type="string",
                description="The remote repository URL to clone.",
            ),
            ToolParameter(
                name="dest",
                type="string",
                description=(
                    "Optional destination folder name within the goblin "
                    "workspace. If omitted, git chooses the folder name."
                ),
                required=False,
            ),
        ],
        handler=_handle_git_clone,
        category="git",
    )
)
