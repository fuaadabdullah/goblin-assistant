"""
Process-level sandbox executor using POSIX resource limits.

Used as the execution backend when SANDBOX_ENABLED=false (no Docker).
Provides CPU, memory, fork, and wall-clock limits without a container.
Suitable for development and single-tenant trusted deployments.

Gaps vs Docker: no filesystem namespace, no network namespace. Stripped PATH
and python3 -I/-S block most naive escapes, but a crafted exploit can still
reach the filesystem and network. Flag for Docker path if untrusted
multi-tenant code is ever in scope — see sandbox_tool.py SANDBOX_ENABLED.
"""

from __future__ import annotations

import asyncio
import os
import resource
import signal
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    RESOURCE_LIMIT = "resource_limit"


@dataclass
class ExecutionResult:
    status: ExecutionStatus
    stdout: str
    stderr: str
    exit_code: Optional[int]
    duration_ms: int
    truncated: bool = field(default=False)


class SandboxLimits:
    # Hard caps — not caller-configurable. The call site clamps the wall
    # timeout to these values before passing it in.
    MAX_CPU_SECONDS: int = int(os.getenv("SANDBOX_CPU_SECONDS", "10"))
    MAX_MEMORY_MB: int = int(os.getenv("SANDBOX_MEMORY_MB", "256"))
    MAX_WALL_SECONDS: int = int(os.getenv("SANDBOX_WALL_SECONDS", "30"))
    MAX_OUTPUT_BYTES: int = int(os.getenv("SANDBOX_OUTPUT_BYTES", str(10 * 1024)))
    MAX_NPROC: int = 1  # no forking — not configurable by design


def _set_resource_limits() -> None:
    """Runs in the child process via preexec_fn — hard caps before exec.

    Called after fork, before exec, so the limits apply to the child and
    everything it spawns. os.setsid() puts the child in its own process group
    so os.killpg() on timeout kills the whole tree, not just the parent.
    """
    rlim_cpu = (SandboxLimits.MAX_CPU_SECONDS, SandboxLimits.MAX_CPU_SECONDS)
    rlim_mem = (SandboxLimits.MAX_MEMORY_MB * 1024 * 1024,) * 2
    rlim_nproc = (SandboxLimits.MAX_NPROC, SandboxLimits.MAX_NPROC)
    rlim_fsize = (1024 * 1024,) * 2  # 1 MB file writes max

    resource.setrlimit(resource.RLIMIT_CPU, rlim_cpu)
    resource.setrlimit(resource.RLIMIT_AS, rlim_mem)
    resource.setrlimit(resource.RLIMIT_NPROC, rlim_nproc)
    resource.setrlimit(resource.RLIMIT_FSIZE, rlim_fsize)
    os.setsid()


# Minimal env: no HOME, no USER, no credentials, no PYTHONPATH side-channels.
_STRIPPED_ENV: dict[str, str] = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONIOENCODING": "utf-8",
}

# -I: isolated mode (ignores PYTHON*, user site, sys.path manipulation)
# -S: no site.py / no site-packages
_LANG_CMD: dict[str, list[str]] = {
    "python": ["python3", "-I", "-S"],
    "javascript": ["node", "--disallow-code-generation-from-strings"],
}

_LANG_SUFFIX: dict[str, str] = {
    "python": ".py",
    "javascript": ".js",
}

_SIGKILL_EXIT = {-signal.SIGKILL, 128 + signal.SIGKILL, 137}


async def execute_code(
    code: str,
    language: str,
    timeout: Optional[int] = None,
) -> ExecutionResult:
    """Execute code with POSIX resource limits. Async-native, no Docker required.

    Args:
        code: Source code to execute.
        language: "python" or "javascript".
        timeout: Wall-clock seconds. Clamped to SandboxLimits.MAX_WALL_SECONDS.
    """
    wall_limit = min(
        timeout if timeout is not None else SandboxLimits.MAX_WALL_SECONDS,
        SandboxLimits.MAX_WALL_SECONDS,
    )
    cmd_prefix = _LANG_CMD.get(language)
    suffix = _LANG_SUFFIX.get(language)
    if cmd_prefix is None or suffix is None:
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            stdout="",
            stderr=f"Unsupported language '{language}'. Use 'python' or 'javascript'.",
            exit_code=-1,
            duration_ms=0,
        )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        script_path = f.name

    loop = asyncio.get_event_loop()
    start = loop.time()
    proc: Optional[asyncio.subprocess.Process] = None

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_prefix,
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=_set_resource_limits,
            cwd=tempfile.gettempdir(),
            env=_STRIPPED_ENV,
        )

        try:
            raw_out, raw_err = await asyncio.wait_for(
                proc.communicate(), timeout=float(wall_limit)
            )
        except asyncio.TimeoutError:
            if proc is not None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await proc.wait()
            duration_ms = int((loop.time() - start) * 1000)
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                stdout="",
                stderr=f"execution exceeded {wall_limit}s wall-clock limit",
                exit_code=-1,
                duration_ms=duration_ms,
            )

    finally:
        Path(script_path).unlink(missing_ok=True)

    duration_ms = int((loop.time() - start) * 1000)
    cap = SandboxLimits.MAX_OUTPUT_BYTES
    truncated = len(raw_out) > cap or len(raw_err) > cap

    returncode = proc.returncode if proc is not None else -1
    if returncode in _SIGKILL_EXIT:
        # SIGKILL = OOM from RLIMIT_AS or RLIMIT_NPROC fork-bomb kill
        status = ExecutionStatus.RESOURCE_LIMIT
    elif returncode == 0:
        status = ExecutionStatus.SUCCESS
    else:
        status = ExecutionStatus.ERROR

    return ExecutionResult(
        status=status,
        stdout=raw_out[:cap].decode(errors="replace"),
        stderr=raw_err[:cap].decode(errors="replace"),
        exit_code=returncode,
        duration_ms=duration_ms,
        truncated=truncated,
    )
