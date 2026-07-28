#!/usr/bin/env python3.11
"""Run phase-gate checks for the repo's rollout path.

The gate runner is intentionally pragmatic:
- it reuses the repo's canonical test buckets where possible
- it runs focused suites for routing and agent-loop coverage
- it can optionally hit live deployment endpoints when URLs are provided
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def _run(command: str) -> int:
    print(f"[phase-gates] $ {command}")
    completed = subprocess.run(command, cwd=ROOT, shell=True, check=False)
    return completed.returncode


def _run_many(commands: Sequence[str]) -> int:
    for command in commands:
        code = _run(command)
        if code != 0:
            return code
    return 0


def _pick_json_value(payload: object, *path: str) -> object:
    current = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | list | str | None = None,
    timeout: float = 30.0,
) -> tuple[int, object]:
    request_body: bytes | None = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if body is not None:
        if isinstance(body, (dict, list)):
            request_body = json.dumps(body).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif isinstance(body, str):
            request_body = body.encode("utf-8")

    request = Request(url, data=request_body, headers=request_headers, method=method)
    with urlopen(request, timeout=timeout) as response:  # nosec: B310 - trusted gate URL
        raw = response.read().decode("utf-8")
        parsed = json.loads(raw) if raw.strip() else {}
        return response.status, parsed


def _env_json(name: str, default: object | None = None) -> object | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return json.loads(raw)


def _live_baseline_checks() -> int:
    backend_url = os.getenv("PHASE_GATES_BACKEND_URL", "").strip()
    frontend_url = os.getenv("PHASE_GATES_FRONTEND_URL", "").strip()
    if backend_url or frontend_url:
        verify_script = ROOT / "scripts" / "verify-deployment.sh"
        if verify_script.exists():
            code = _run(f"bash {verify_script}")
            if code != 0:
                return code

    chat_url = os.getenv("PHASE_GATES_CHAT_URL", "").strip()
    if not chat_url:
        return 0

    headers = _env_json("PHASE_GATES_CHAT_HEADERS_JSON", {}) or {}
    payload = _env_json("PHASE_GATES_CHAT_PAYLOAD_JSON", {}) or {}
    if not isinstance(headers, dict) or not isinstance(payload, (dict, list)):
        print("[phase-gates] invalid chat smoke JSON env")
        return 2

    method = os.getenv("PHASE_GATES_CHAT_METHOD", "POST").strip().upper() or "POST"
    try:
        status, response = _http_json(chat_url, method=method, headers=headers, body=payload)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"[phase-gates] chat round-trip request failed: {exc}")
        return 1

    if status >= 400:
        print(f"[phase-gates] chat round-trip returned HTTP {status}")
        return 1

    conversation_id = (
        _pick_json_value(response, "conversation_id")
        or _pick_json_value(response, "data", "conversation_id")
        or _pick_json_value(response, "data", "task", "conversation_id")
        or _pick_json_value(response, "task", "conversation_id")
    )

    fetch_template = os.getenv("PHASE_GATES_CHAT_FETCH_URL_TEMPLATE", "").strip()
    if fetch_template and conversation_id:
        fetch_url = fetch_template.format(conversation_id=conversation_id)
        try:
            fetch_status, fetch_response = _http_json(fetch_url)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"[phase-gates] chat persistence fetch failed: {exc}")
            return 1
        if fetch_status >= 400:
            print(f"[phase-gates] chat persistence fetch returned HTTP {fetch_status}")
            return 1
        if not fetch_response:
            print("[phase-gates] chat persistence fetch returned an empty payload")
            return 1

    print("[phase-gates] baseline live checks passed")
    return 0


def _baseline() -> int:
    return _run_many(
        [
            "make PYTHON=python3.11 test-integration",
            "make PYTHON=python3.11 test-web",
        ]
    )


def _routing() -> int:
    return _run_many(
        [
            'cd apps/api && PYTHONPATH=src python3.11 -m pytest -o "addopts=" -v '
            "../../tests/contract/test_engine_routing_contract.py "
            "src/api/tests/test_router_service.py "
            "src/api/tests/provider_dispatcher_routing/",
        ]
    )


def _agent() -> int:
    return _run_many(
        [
            'cd apps/api && PYTHONPATH=src python3.11 -m pytest -o "addopts=" -v '
            "src/api/tests/test_agent_router.py "
            "src/api/tests/test_agent_workflow.py "
            "src/api/tests/test_github_tool.py",
        ]
    )


def _benchmarks() -> int:
    return _run_many(
        [
            'cd apps/api && PYTHONPATH=src python3.11 -m pytest -o "addopts=" -v '
            "src/api/tests/test_benchmark_catalog.py",
            'cd apps/api && PYTHONPATH=src python3.11 -m benchmarks.runner '
            "--dry-run --limit 3 --report",
            'cd apps/api && PYTHONPATH=src python3.11 -m benchmarks.memory.runner '
            "--dry-run --scenarios hardware-inventory contradiction-handling",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run phase-gate checks.")
    parser.add_argument(
        "gate",
        choices=("baseline", "routing", "agent", "benchmarks", "all"),
        help="Which gate to evaluate",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live deployment smoke checks when supported by environment variables.",
    )
    args = parser.parse_args(argv)

    if args.gate == "baseline":
        code = _baseline()
        if code == 0 and args.live:
            code = _live_baseline_checks()
        return code

    if args.gate == "routing":
        return _routing()

    if args.gate == "agent":
        return _agent()

    if args.gate == "benchmarks":
        return _benchmarks()

    for gate_runner in (_baseline, _routing, _agent):
        code = gate_runner()
        if code != 0:
            return code
    code = _benchmarks()
    if code != 0:
        return code
    if args.live:
        return _live_baseline_checks()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
