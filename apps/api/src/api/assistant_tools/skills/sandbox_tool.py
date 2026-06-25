"""
Sandbox execution tools for Goblin Assistant.

Registers tools that let the LLM execute arbitrary Python or JavaScript code
and run pre-built financial analysis templates in a controlled environment.

Execution strategy:
  SANDBOX_ENABLED=true  → Docker container (network-isolated, read-only mount)
  SANDBOX_ENABLED=false → direct subprocess (development mode, no Docker required)
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


def _run_code(code: str, language: str, timeout: int) -> Dict[str, Any]:
    """Write code to a tempfile and execute it synchronously.

    Called from inside asyncio.to_thread, so this may block freely.
    """
    _LANG_FILE = {"python": "main.py", "javascript": "main.js"}
    filename = _LANG_FILE.get(language)
    if filename is None:
        return {"error": f"Unsupported language '{language}'. Use 'python' or 'javascript'."}

    sandbox_enabled = os.getenv("SANDBOX_ENABLED", "false").lower() == "true"
    sandbox_image = os.getenv("SANDBOX_IMAGE", "goblin-assistant-sandbox:latest")

    with tempfile.TemporaryDirectory() as tmpdir:
        code_path = Path(tmpdir) / filename
        code_path.write_text(code, encoding="utf-8")

        if sandbox_enabled:
            sandbox_user = os.getenv("SANDBOX_USER", "runner")
            cmd = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--memory",
                "256m",
                "--cpus",
                "0.5",
                "--read-only",
                "--cap-drop",
                "all",
                "--security-opt",
                "no-new-privileges",
                "--user",
                sandbox_user,
                "--tmpfs",
                "/tmp:size=64m,mode=1777",
                "-v",
                f"{tmpdir}:/code:ro",
                sandbox_image,
                "python" if language == "python" else "node",
                f"/code/{filename}",
            ]
        else:
            interpreter = "python" if language == "python" else "node"
            cmd = [interpreter, str(code_path)]

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
            interp = "docker" if sandbox_enabled else ("python" if language == "python" else "node")
            return {"error": f"Interpreter not found: '{interp}'", "exit_code": -1}

    truncated = len(result.stdout) > _STDOUT_CAP
    return {
        "stdout": result.stdout[:_STDOUT_CAP],
        "stderr": result.stderr[:_STDOUT_CAP],
        "exit_code": result.returncode,
        "truncated": truncated,
        "sandbox_enabled": sandbox_enabled,
    }


# ---------------------------------------------------------------------------
# execute_code
# ---------------------------------------------------------------------------


async def _handle_execute_code(
    code: str,
    language: str = "python",
    timeout: int = 30,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        if not code or not code.strip():
            return {"error": "code cannot be empty"}
        if language not in ("python", "javascript"):
            return {"error": f"Unsupported language '{language}'. Use 'python' or 'javascript'."}
        clamped = max(1, min(timeout, 120))
        return _run_code(code, language, clamped)

    return await asyncio.to_thread(_run)


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
    def _run() -> Dict[str, Any]:
        template = get_template(template_name)
        if template is None:
            available = ", ".join(t["name"] for t in list_templates())
            return {"error": (f"Unknown template '{template_name}'. Available: {available}")}

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

        return _run_code(code, "python", timeout=60)

    return await asyncio.to_thread(_run)


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
