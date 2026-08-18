"""
Sandbox execution tools for Goblin Assistant.

Registers tools that let the LLM execute arbitrary Python or JavaScript code
and run pre-built financial analysis templates in a controlled environment.

Execution strategy:
  SANDBOX_ENABLED=true  → Docker container (network-isolated, read-only mount)
  SANDBOX_ENABLED=false → process-level POSIX resource limits (dev/no-Docker path)

Hardening (when Docker is enabled):
  - Network: none
  - Memory: 256 MB
  - CPU: 0.5 cores
  - PIDs: max 32
  - Filesystem: read-only root, noexec/nosuid/nodev tmpfs
  - Capabilities: all dropped
  - no-new-privileges enforced
  - User: non-root runner
  - ulimits: nproc=32:64, fsize=1MB, nofile=64

Hardening (SANDBOX_ENABLED=false, via sandbox_executor):
  - RLIMIT_CPU, RLIMIT_AS, RLIMIT_NPROC, RLIMIT_FSIZE applied via preexec_fn
  - setsid + killpg ensures whole process tree is killed on wall-clock timeout
  - python3 -I -S strips site-packages and env-variable injection
  - Stripped PATH env; no HOME/USER/PYTHONPATH
  Gap: no filesystem or network namespace — suitable for dev/trusted deployments only.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from ..registry import ToolDefinition, ToolParameter, register_tool
from ..sandbox_templates import get_template, list_templates

_STDOUT_CAP: int = 10 * 1024  # 10 KB


def _run_docker_code(code: str, language: str, timeout: int) -> Dict[str, Any]:
    """Execute code inside a Docker container with full hardening.

    Blocking — intended to be called via asyncio.to_thread.
    Only called when SANDBOX_ENABLED=true.
    """
    _LANG_FILE = {"python": "main.py", "javascript": "main.js"}
    filename = _LANG_FILE.get(language)
    if filename is None:
        return {"error": f"Unsupported language '{language}'. Use 'python' or 'javascript'."}

    sandbox_image = os.getenv("SANDBOX_IMAGE", "goblin-assistant-sandbox:latest")
    sandbox_user = os.getenv("SANDBOX_USER", "runner")

    with tempfile.TemporaryDirectory() as tmpdir:
        code_path = Path(tmpdir) / filename
        code_path.write_text(code, encoding="utf-8")

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            "256m",
            "--memory-swap",
            "256m",
            "--cpus",
            "0.5",
            "--pids-limit",
            "32",
            "--read-only",
            "--cap-drop",
            "all",
            "--security-opt",
            "no-new-privileges",
            "--user",
            sandbox_user,
            "--tmpfs",
            "/tmp:size=64m,noexec,nosuid,nodev,mode=1777",
            "--tmpfs",
            f"/home/{sandbox_user}:size=32m,noexec,nosuid,nodev,mode=1777",
            "--ulimit",
            "nproc=32:64",
            "--ulimit",
            "fsize=1048576",
            "--ulimit",
            "nofile=64",
            "-v",
            f"{tmpdir}:/code:ro",
            sandbox_image,
            "python" if language == "python" else "node",
            f"/code/{filename}",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"error": f"Execution timed out after {timeout}s", "exit_code": -1}
        except FileNotFoundError:
            return {
                "error": "Docker not found — set SANDBOX_ENABLED=false for dev mode",
                "exit_code": -1,
            }

    truncated = len(result.stdout) > _STDOUT_CAP
    return {
        "stdout": result.stdout[:_STDOUT_CAP],
        "stderr": result.stderr[:_STDOUT_CAP],
        "exit_code": result.returncode,
        "truncated": truncated,
        "sandbox_enabled": True,
    }


# ---------------------------------------------------------------------------
# execute_code
# ---------------------------------------------------------------------------


async def _handle_execute_code(
    code: str,
    language: str = "python",
    timeout: int = 30,
) -> Dict[str, Any]:
    if not code or not code.strip():
        return {"error": "code cannot be empty"}
    if language not in ("python", "javascript"):
        return {"error": f"Unsupported language '{language}'. Use 'python' or 'javascript'."}
    clamped = max(1, min(timeout, 120))

    if os.getenv("SANDBOX_ENABLED", "false").lower() == "true":
        return await asyncio.to_thread(_run_docker_code, code, language, clamped)

    # Dev / no-Docker path: process-level POSIX resource limits.
    from ...services.sandbox_executor import ExecutionStatus
    from ...services.sandbox_executor import execute_code as _exec

    result = await _exec(code, language, timeout=clamped)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "truncated": result.truncated,
        "duration_ms": result.duration_ms,
        "sandbox_enabled": False,
        "status": result.status.value,
        # Surface resource-limit kills clearly so the LLM can explain them.
        **(
            {"error": "process killed by resource limit (OOM or fork)"}
            if result.status == ExecutionStatus.RESOURCE_LIMIT
            else {}
        ),
        **(
            {"error": f"execution timed out after {clamped}s"}
            if result.status == ExecutionStatus.TIMEOUT
            else {}
        ),
    }


register_tool(
    ToolDefinition(
        name="execute_code",
        description=(
            "Use when the user wants to run a snippet of Python or JavaScript code "
            "and see the output. Executes in an isolated environment with no network "
            "access. Returns stdout, stderr, and the exit code. Stdout is capped at "
            "10 KB. Prefer this over shell commands for computation or data analysis."
        ),
        parameters=[
            ToolParameter(
                name="code",
                type="string",
                description="The source code to execute. Must be valid Python or JavaScript.",
            ),
            ToolParameter(
                name="language",
                type="string",
                description="Programming language: 'python' (default) or 'javascript'.",
                required=False,
                default="python",
                enum=["python", "javascript"],
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Maximum execution time in seconds. Defaults to 30. Max 120.",
                required=False,
                default=30,
            ),
        ],
        handler=_handle_execute_code,
        category="terminal",
    )
)


# ---------------------------------------------------------------------------
# run_sandbox_template
# ---------------------------------------------------------------------------


async def _handle_run_sandbox_template(
    template_name: str,
    parameters: str,
) -> Dict[str, Any]:
    template = get_template(template_name)
    if template is None:
        available = ", ".join(t["name"] for t in list_templates())
        return {"error": f"Unknown template '{template_name}'. Available: {available}"}

    try:
        params = json.loads(parameters)
    except json.JSONDecodeError as exc:
        return {"error": f"parameters must be valid JSON: {exc}"}

    if not isinstance(params, dict):
        return {"error": "parameters must be a JSON object (dict), not an array or scalar"}

    try:
        code = template.render(**params)
    except KeyError as exc:
        return {"error": f"Missing template parameter: {exc}"}

    if os.getenv("SANDBOX_ENABLED", "false").lower() == "true":
        return await asyncio.to_thread(_run_docker_code, code, "python", 60)

    from ...services.sandbox_executor import execute_code as _exec

    result = await _exec(code, "python", timeout=60)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "truncated": result.truncated,
        "duration_ms": result.duration_ms,
        "sandbox_enabled": False,
        "status": result.status.value,
    }


register_tool(
    ToolDefinition(
        name="run_sandbox_template",
        description=(
            "Use when the user wants to run a pre-built financial analysis template "
            "such as Monte Carlo portfolio simulation, portfolio backtesting, or "
            "compound interest calculation. Pass the template name and its parameters "
            "as a JSON object string. Returns the JSON output printed by the template. "
            "Call this instead of execute_code for known financial analyses. "
            "Available templates: 'monte_carlo_portfolio', 'backtest_allocation', "
            "'compound_interest'."
        ),
        parameters=[
            ToolParameter(
                name="template_name",
                type="string",
                description=(
                    "Name of the template to run. Available: "
                    "'monte_carlo_portfolio', 'backtest_allocation', 'compound_interest'."
                ),
            ),
            ToolParameter(
                name="parameters",
                type="string",
                description=(
                    "JSON string of template parameters, e.g. "
                    '\'{"principal": 10000, "annual_rate": 0.07, '
                    '"years": 30, "monthly_contribution": 500}\'. '
                    "Check the template's parameter list for required keys."
                ),
            ),
        ],
        handler=_handle_run_sandbox_template,
        category="terminal",
    )
)
