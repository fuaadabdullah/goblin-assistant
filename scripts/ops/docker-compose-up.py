#!/usr/bin/env python3
"""Start the lean API stack with a single-flight Docker Compose guard.

The lock prevents two repository-owned launches from racing. Before launch,
legacy compose commands targeting the backend service are terminated so an
old hung build cannot later replace a healthy container.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = REPO_ROOT / ".tmp" / "api-docker-up.lock"
COMPOSE_PATTERN = re.compile(
    r"(?:docker(?:\.exe)?\s+compose|docker-compose(?:\.exe)?)"
    r".*\b(?:up|build)\b.*\bgoblin-assistant-backend\b",
    re.IGNORECASE,
)


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def process_command(pid: int) -> str:
    if os.name == "nt":
        command = (
            f'$p = Get-CimInstance Win32_Process -Filter "ProcessId = {pid}"; '
            "if ($p) { Write-Output $p.CommandLine }"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()

    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def list_processes() -> list[tuple[int, str]]:
    if os.name == "nt":
        command = (
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        raw = json.loads(result.stdout)
        rows = raw if isinstance(raw, list) else [raw]
        return [
            (int(row["ProcessId"]), str(row.get("CommandLine") or ""))
            for row in rows
            if row.get("ProcessId")
        ]

    result = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        capture_output=True,
        text=True,
        check=False,
    )
    processes: list[tuple[int, str]] = []
    for line in result.stdout.splitlines():
        match = re.match(r"\s*(\d+)\s+(.*)", line)
        if match:
            processes.append((int(match.group(1)), match.group(2)))
    return processes


def terminate_process(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and process_exists(pid):
        time.sleep(0.1)
    if process_exists(pid):
        os.kill(pid, signal.SIGKILL)


def acquire_lock() -> int:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                lock_data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
                owner_pid = int(lock_data.get("pid", 0))
            except (OSError, ValueError, json.JSONDecodeError):
                owner_pid = 0

            owner_command = (
                process_command(owner_pid) if process_exists(owner_pid) else ""
            )
            if owner_command and "docker-compose-up.py" in owner_command:
                raise RuntimeError(
                    f"another API Docker launch is already active (PID {owner_pid})"
                )
            LOCK_PATH.unlink(missing_ok=True)
            continue

        os.write(
            fd,
            json.dumps({"pid": os.getpid(), "started_at": time.time()}).encode("utf-8"),
        )
        return fd


def stop_legacy_compose_processes() -> None:
    stale_processes = [
        (pid, command)
        for pid, command in list_processes()
        if pid != os.getpid() and COMPOSE_PATTERN.search(command)
    ]
    if not stale_processes:
        print("==> Guard: no stale backend Docker Compose process found.")
        return

    for pid, _command in stale_processes:
        print(f"==> Guard: stopping stale backend Docker Compose process PID {pid}.")
        terminate_process(pid)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--legacy", action="store_true", help="disable BuildKit for this launch"
    )
    args = parser.parse_args()

    try:
        lock_fd = acquire_lock()
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    try:
        stop_legacy_compose_processes()
        environment = os.environ.copy()
        if args.legacy:
            environment.update(
                {"DOCKER_BUILDKIT": "0", "COMPOSE_DOCKER_CLI_BUILD": "0"}
            )
        command = [
            "docker",
            "compose",
            "--project-name",
            "goblin-assistant",
            "up",
            "-d",
            "redis",
            "goblin-assistant-backend",
        ]
        return subprocess.run(
            command, cwd=REPO_ROOT, env=environment, check=False
        ).returncode
    finally:
        os.close(lock_fd)
        LOCK_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
