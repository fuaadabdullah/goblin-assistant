#!/usr/bin/env python3
"""SLO smoke-load harness for Goblin Assistant.

Exercises the cheap, always-on endpoints behind the documented SLOs
(`docs/operations/SLO.md`) against a running API instance:

- GET  /health                 -> API Availability SLO (no 5xx under load)
- GET  /api/v1/health          -> versioned health alias
- GET  /api/v1/auth/csrf-token -> auth path liveness (CSRF issuance)

Exit code is 0 only when every check passes its budget:
- 0 server errors (5xx/transport) on health endpoints
- P95 latency within --max-p95-ms (default 2000ms, the Chat P95 SLO ceiling
  used here as a proxy for backend responsiveness)

Deliberately avoids LLM-backed chat/completions endpoints: those burn
provider quota and have nondeterministic latency. Point the harness at a
staging instance with GOBLIN_API_BASE_URL to measure a deployed environment.
All tuning is via env vars so the same script runs locally, in CI smoke,
and in nightly load:

    GOBLIN_API_BASE_URL   base URL (default http://127.0.0.1:8001)
    GOBLIN_API_KEY        x-api-key for versioned endpoints
    LOAD_CONCURRENCY      concurrent clients per endpoint (default 10)
    LOAD_REQUESTS         total requests per endpoint (default 100)
    LOAD_MAX_P95_MS       P95 budget in ms (default 2000)
    LOAD_TIMEOUT_S        per-request timeout in seconds (default 15)

Requires: aiohttp (already an API dependency).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field

try:
    import aiohttp
except ImportError:  # pragma: no cover - surfaced as a clear CLI error
    print("ERROR: aiohttp is required (pip install aiohttp)", file=sys.stderr)
    sys.exit(2)


@dataclass
class EndpointBudget:
    path: str
    ok_statuses: tuple[int, ...] = (200,)
    needs_api_key: bool = False


@dataclass
class EndpointResult:
    path: str
    total: int = 0
    ok: int = 0
    status_5xx: int = 0
    other_failures: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def p50_ms(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        if len(self.latencies_ms) == 1:
            return self.latencies_ms[0]
        ordered = sorted(self.latencies_ms)
        rank = max(1, -(-95 * len(ordered) // 100))  # nearest-rank method
        return ordered[rank - 1]


async def _hit(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict[str, str],
    timeout_s: float,
) -> tuple[float, int, str]:
    start = time.perf_counter()
    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout_s)
        ) as response:
            await response.read()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return elapsed_ms, response.status, ""
    except Exception as exc:  # noqa: BLE001 - transport errors are failures
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms, 0, f"{type(exc).__name__}: {exc}"


async def _run_endpoint(
    base_url: str,
    budget: EndpointBudget,
    api_key: str,
    concurrency: int,
    total: int,
    timeout_s: float,
) -> EndpointResult:
    result = EndpointResult(path=budget.path)
    headers: dict[str, str] = {}
    if budget.needs_api_key and api_key:
        headers["x-api-key"] = api_key
    sem = asyncio.Semaphore(max(1, concurrency))

    async def _one(session: aiohttp.ClientSession) -> None:
        async with sem:
            elapsed_ms, status, error = await _hit(
                session, f"{base_url}{budget.path}", headers, timeout_s
            )
        result.total += 1
        result.latencies_ms.append(elapsed_ms)
        if status in budget.ok_statuses:
            result.ok += 1
        elif 500 <= status <= 599 or status == 0:
            result.status_5xx += 1
            if error:
                result.errors.append(error[:200])
        else:
            result.other_failures += 1
            label = f"status={status}" + (f" {error[:120]}" if error else "")
            result.errors.append(label)

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(_one(session) for _ in range(total)))
    return result


def _check(result: EndpointResult, max_p95_ms: float) -> list[str]:
    failures: list[str] = []
    if result.status_5xx:
        failures.append(
            f"{result.path}: {result.status_5xx} server errors (5xx/transport)"
        )
    if result.other_failures:
        sample = "; ".join(result.errors[:2])
        failures.append(
            f"{result.path}: {result.other_failures} non-OK responses [{sample}]"
        )
    if result.p95_ms > max_p95_ms:
        failures.append(
            f"{result.path}: p95 {result.p95_ms:.0f}ms exceeds budget {max_p95_ms:.0f}ms"
        )
    return failures


async def _run_all(args: argparse.Namespace) -> tuple[list[EndpointResult], list[str]]:
    budgets = [
        EndpointBudget(path="/health"),
        EndpointBudget(path="/api/v1/health"),
        EndpointBudget(path="/api/v1/auth/csrf-token"),
    ]
    results = [
        await _run_endpoint(
            args.base_url.rstrip("/"),
            budget,
            args.api_key,
            args.concurrency,
            args.requests,
            args.timeout_s,
        )
        for budget in budgets
    ]
    failures: list[str] = []
    for result in results:
        failures.extend(_check(result, args.max_p95_ms))
    return results, failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SLO smoke-load harness (see module docstring)."
    )
    parser.add_argument(
        "--base-url", default=os.getenv("GOBLIN_API_BASE_URL", "http://127.0.0.1:8001")
    )
    parser.add_argument("--api-key", default=os.getenv("GOBLIN_API_KEY", ""))
    parser.add_argument(
        "--concurrency", type=int, default=int(os.getenv("LOAD_CONCURRENCY", "10"))
    )
    parser.add_argument(
        "--requests", type=int, default=int(os.getenv("LOAD_REQUESTS", "100"))
    )
    parser.add_argument(
        "--max-p95-ms", type=float, default=float(os.getenv("LOAD_MAX_P95_MS", "2000"))
    )
    parser.add_argument(
        "--timeout-s", type=float, default=float(os.getenv("LOAD_TIMEOUT_S", "15"))
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    args = parser.parse_args()

    results, failures = asyncio.run(_run_all(args))

    if args.json:
        print(
            json.dumps(
                {
                    "base_url": args.base_url,
                    "budget_p95_ms": args.max_p95_ms,
                    "endpoints": [
                        {
                            "path": r.path,
                            "total": r.total,
                            "ok": r.ok,
                            "server_errors": r.status_5xx,
                            "other_failures": r.other_failures,
                            "p50_ms": round(r.p50_ms, 1),
                            "p95_ms": round(r.p95_ms, 1),
                        }
                        for r in results
                    ],
                    "failures": failures,
                },
                indent=2,
            )
        )
    else:
        print(
            f"SLO smoke-load vs {args.base_url} "
            f"({args.requests} req x {args.concurrency} concurrent, "
            f"p95 budget {args.max_p95_ms:.0f}ms)"
        )
        for r in results:
            print(
                f"  {r.path}: ok={r.ok}/{r.total} "
                f"5xx={r.status_5xx} other={r.other_failures} "
                f"p50={r.p50_ms:.0f}ms p95={r.p95_ms:.0f}ms"
            )
        if failures:
            print("FAIL:")
            for failure in failures:
                print(f"  - {failure}")
        else:
            print("PASS: all endpoints within SLO budgets.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
