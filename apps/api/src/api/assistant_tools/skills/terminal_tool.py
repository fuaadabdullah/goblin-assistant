"""
Terminal tools for Goblin Assistant.

Registers tools for running shell commands in the goblin workspace.
All operations are sandboxed to the GOBLIN_FILE_WORKSPACE directory
to prevent directory traversal.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from ..registry import ToolDefinition, ToolParameter, register_tool


def _get_base_dir() -> Path:
    """Return the resolved sandbox base directory."""
    raw = os.environ.get("GOBLIN_FILE_WORKSPACE", "~/goblin-workspace")
    return Path(raw).expanduser().resolve()


def _resolve_working_dir(user_path: str) -> Path:
    """Resolve user_path inside the workspace; raise ValueError if it escapes."""
    base = _get_base_dir()
    candidate = (base / user_path).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError(
            f"working_directory '{user_path}' resolves outside the workspace. "
            "All shell commands must run within the goblin workspace."
        )
    if not candidate.exists():
        raise ValueError(f"working_directory does not exist: {user_path}")
    if not candidate.is_dir():
        raise ValueError(f"working_directory is not a directory: {user_path}")
    return candidate


# ---------------------------------------------------------------------------
# run_shell_command
# ---------------------------------------------------------------------------


async def _handle_run_shell_command(
    command: str,
    working_directory: str = ".",
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        if not command or not command.strip():
            return {"error": "command cannot be empty"}

        try:
            cwd = _resolve_working_dir(working_directory)
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            args = shlex.split(command)
        except ValueError as exc:
            return {"error": f"Could not parse command: {exc}"}

        if not args:
            return {"error": "command parsed to empty argument list"}

        start = time.monotonic()
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(cwd),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out after 30 seconds", "exit_code": -1}
        except FileNotFoundError:
            return {"error": f"Command not found: '{args[0]}'", "exit_code": -1}

        elapsed_ms = int((time.monotonic() - start) * 1000)

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "elapsed_ms": elapsed_ms,
            "working_directory": str(cwd),
        }

    return await asyncio.to_thread(_run)


register_tool(
    ToolDefinition(
        name="run_shell_command",
        description=(
            "Use when the user wants to run a shell command in the goblin workspace "
            "directory — for example to list files, run a build script, check a "
            "Python version, or inspect environment variables. Commands are parsed "
            "with shlex (no shell expansion) and run with a 30-second timeout. "
            "The working directory must be within the goblin workspace. "
            "For code execution with isolation, use execute_code instead."
        ),
        parameters=[
            ToolParameter(
                name="command",
                type="string",
                description=(
                    "The shell command to run, e.g. 'ls -la' or 'python --version'. "
                    "Parsed with shlex — no shell glob or variable expansion."
                ),
            ),
            ToolParameter(
                name="working_directory",
                type="string",
                description=(
                    "Directory to run the command in, relative to the goblin workspace "
                    "root. Defaults to '.' (workspace root)."
                ),
                required=False,
                default=".",
            ),
        ],
        handler=_handle_run_shell_command,
        category="terminal",
    )
)
