"""
Goblin intelligence layer benchmark runner.

Runs a dataset of prompts against multiple routing strategies and records
cost, latency, TTFT, success, fallback usage, and answer quality for each.

Usage (from apps/api/):
  python -m benchmarks.runner
  python -m benchmarks.runner --strategies goblin cheapest strongest
  python -m benchmarks.runner --categories coding reasoning --limit 10
  python -m benchmarks.runner --llm-judge --out results/my_run.jsonl
  python -m benchmarks.runner --dry-run        # print plan, no API calls

Output:
  JSONL file in benchmarks/results/run_<timestamp>.jsonl
  One record per (prompt, strategy) pair.

Record schema:
  {
    "run_id": str,          # shared across all records in one run
    "prompt_id": str,
    "category": str,
    "difficulty": int,
    "strategy": str,        # goblin | cheapest | strongest | random
    "selected_provider": str | null,
    "selected_model": str | null,
    "success": bool,
    "used_fallback": bool,  # provider differed from the first candidate
    "ttft_ms": float | null,
    "latency_ms": float | null,
    "input_tokens": int | null,
    "output_tokens": int | null,
    "cost_usd": float | null,
    "quality_score": float, # 0.0-1.0
    "judge": str,           # "heuristic" | "llm"
    "error": str | null,
    "timestamp": str,
  }
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent

# Ensure `api` and `benchmarks` packages are importable regardless of CWD.
_api_root = HERE.parent  # apps/api/
_src = _api_root / "src"  # apps/api/src/ — where api package lives
for _p in (_src, _api_root):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
DATASET_PATH = HERE / "dataset" / "prompts.jsonl"
RESULTS_DIR = HERE / "results"

ALL_STRATEGIES = ["goblin", "cheapest", "strongest", "random"]
ALL_CATEGORIES = [
    "simple",
    "casual",
    "coding",
    "research",
    "reasoning",
    "long_context",
    "memory_retrieval",
    "finance",
    "tool_usage",
    "difficult",
]


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def load_prompts(
    categories: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    prompts = []
    with open(DATASET_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            if categories and p.get("category") not in categories:
                continue
            prompts.append(p)
    if limit:
        prompts = prompts[:limit]
    return prompts


# ---------------------------------------------------------------------------
# TTFT measurement via streaming
# ---------------------------------------------------------------------------


async def _invoke_with_ttft(
    dispatcher: Any,
    pid: Optional[str],
    model: Optional[str],
    messages: List[Dict[str, str]],
    timeout_ms: int,
) -> Dict[str, Any]:
    """
    Invoke using the streaming path and measure time-to-first-token.

    The dispatcher already handles provider fallback. We stream the actual
    response so TTFT is measured from the first emitted chunk instead of being
    inferred from wall-clock latency.

    Returns a dict with keys: ok, text, provider, model, latency_ms,
    ttft_ms, input_tokens, output_tokens, cost_usd, error.
    """
    payload = {"messages": messages}
    t0 = time.perf_counter()
    ttft_ms: Optional[float] = None
    try:
        result = await asyncio.wait_for(
            dispatcher.dispatch(
                pid=pid,
                model=model,
                payload=payload,
                timeout_ms=timeout_ms,
                stream=True,
            ),
            timeout=timeout_ms / 1000 + 5,
        )
    except asyncio.TimeoutError:
        return {
            "ok": False,
            "text": "",
            "provider": None,
            "model": None,
            "latency_ms": timeout_ms,
            "ttft_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "error": "timeout",
        }
    except Exception as exc:
        return {
            "ok": False,
            "text": "",
            "provider": None,
            "model": None,
            "latency_ms": (time.perf_counter() - t0) * 1000,
            "ttft_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "error": str(exc),
        }

    if not result.get("ok"):
        return {
            "ok": False,
            "text": "",
            "provider": result.get("provider"),
            "model": result.get("model"),
            "latency_ms": (time.perf_counter() - t0) * 1000,
            "ttft_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "error": result.get("error") or "stream_failed",
        }

    stream = result.get("stream")
    if stream is None:
        return {
            "ok": False,
            "text": "",
            "provider": result.get("provider"),
            "model": result.get("model"),
            "latency_ms": (time.perf_counter() - t0) * 1000,
            "ttft_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "error": "stream_missing",
        }

    chunks: List[str] = []
    try:
        async for chunk in stream:
            text = str(chunk.get("text") or chunk.get("content") or "")
            if not text:
                continue
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - t0) * 1000
            chunks.append(text)
    except Exception as exc:
        return {
            "ok": False,
            "text": "".join(chunks),
            "provider": result.get("provider"),
            "model": result.get("model"),
            "latency_ms": (time.perf_counter() - t0) * 1000,
            "ttft_ms": ttft_ms,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "error": str(exc),
        }

    latency_ms = (time.perf_counter() - t0) * 1000
    text = "".join(chunks)
    usage = result.get("usage") or {}
    input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
    output_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
    cost_usd = result.get("cost_usd")
    try:
        from api.core.tokenization import count_tokens  # noqa: PLC0415

        if input_tokens is None and messages:
            input_tokens = count_tokens(messages[-1].get("content", ""))
        if output_tokens is None:
            output_tokens = count_tokens(text)
    except Exception:
        pass
    if (
        cost_usd is None
        and result.get("provider")
        and result.get("model")
    ):
        try:
            from api.providers.pricing import estimate_cost  # noqa: PLC0415

            if input_tokens is not None and output_tokens is not None:
                cost_usd = estimate_cost(
                    result["provider"],
                    int(input_tokens),
                    int(output_tokens),
                    model=result.get("model"),
                )
        except Exception:
            pass
    if cost_usd is None and text.strip():
        cost_usd = 0.0
    return {
        "ok": bool(text.strip()) or result.get("ok", False),
        "text": text,
        "provider": result.get("provider"),
        "model": result.get("model"),
        "latency_ms": latency_ms,
        "ttft_ms": ttft_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "error": result.get("error") if not result.get("ok") else None,
    }


# ---------------------------------------------------------------------------
# Single prompt × strategy execution
# ---------------------------------------------------------------------------


async def run_one(
    prompt: Dict[str, Any],
    strategy: str,
    *,
    judge: Any,
    judge_name: str,
    dispatcher: Any,
    timeout_ms: int,
    run_id: str,
    concurrency_sem: asyncio.Semaphore,
    verbose: bool = False,
) -> Dict[str, Any]:
    from benchmarks.baselines import STRATEGIES  # noqa: PLC0415

    strategy_fn = STRATEGIES[strategy]
    pid, model = strategy_fn()

    async with concurrency_sem:
        result = await _invoke_with_ttft(
            dispatcher,
            pid,
            model,
            [{"role": "user", "content": prompt["prompt"]}],
            timeout_ms,
        )

    succeeded = result["ok"] and bool(result.get("text", "").strip())

    # Determine if fallback was used: compare the provider that actually
    # answered with the first provider the dispatcher would have tried.
    baseline_provider = pid
    baseline_model = model
    if strategy == "goblin":
        candidate_order = dispatcher._candidate_order(pid)  # noqa: SLF001
        configured_candidates = dispatcher._auto_configured_candidates(candidate_order)  # noqa: SLF001
        if not configured_candidates:
            configured_candidates = [
                p for p in candidate_order if dispatcher.is_configured(p)
            ]
        baseline_provider = configured_candidates[0] if configured_candidates else None
        if baseline_provider is not None:
            baseline_model = dispatcher.get_provider_config(baseline_provider).get("default_model")
    used_fallback = bool(
        baseline_provider
        and result.get("provider")
        and result.get("provider") != baseline_provider
    )

    # Score quality
    if asyncio.iscoroutinefunction(judge.score):
        quality = await judge.score(result.get("text", ""), prompt, succeeded=succeeded)
    else:
        quality = judge.score(result.get("text", ""), prompt, succeeded=succeeded)

    # Cost estimate: use reported cost, fall back to pricing module
    cost = result.get("cost_usd")
    if (
        cost is None
        and succeeded
        and result.get("input_tokens")
        and result.get("output_tokens")
    ):
        try:
            from api.providers.pricing import estimate_cost  # noqa: PLC0415

            cost = estimate_cost(
                result["provider"] or "",
                int(result["input_tokens"]),
                int(result["output_tokens"]),
                model=result.get("model"),
            )
        except Exception:
            pass

    record = {
        "run_id": run_id,
        "prompt_id": prompt["id"],
        "prompt": prompt.get("prompt"),
        "category": prompt.get("category"),
        "difficulty": prompt.get("difficulty"),
        "strategy": strategy,
        "requested_provider": pid,
        "requested_model": model,
        "baseline_provider": baseline_provider,
        "baseline_model": baseline_model,
        "selected_provider": result.get("provider"),
        "selected_model": result.get("model"),
        "success": succeeded,
        "used_fallback": used_fallback,
        "ttft_ms": result.get("ttft_ms"),
        "latency_ms": result.get("latency_ms"),
        "input_tokens": result.get("input_tokens"),
        "output_tokens": result.get("output_tokens"),
        "cost_usd": cost,
        "quality_score": round(quality, 4),
        "judge": judge_name,
        "error": result.get("error"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if verbose:
        status = "✓" if succeeded else "✗"
        q = f"q={quality:.2f}"
        lat = f"{result.get('latency_ms', 0):.0f}ms"
        ttft = f"ttft={result.get('ttft_ms', 0):.0f}ms" if result.get("ttft_ms") is not None else "ttft=n/a"
        cost_str = f"${cost:.5f}" if cost else "  free"
        prov = result.get("provider") or "?"
        print(
            f"  {status} [{strategy:<10}] {prompt['id']:<10} "
            f"{prov:<16} {lat:>8} {ttft:>12} {cost_str:>10} {q}"
        )

    return record


# ---------------------------------------------------------------------------
# Main run loop
# ---------------------------------------------------------------------------


async def run_benchmark(
    prompts: List[Dict[str, Any]],
    strategies: List[str],
    *,
    llm_judge: bool = False,
    out_path: Path,
    timeout_ms: int = 30_000,
    concurrency: int = 4,
    verbose: bool = False,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    from api.providers.dispatcher import dispatcher  # noqa: PLC0415
    from benchmarks.judge import HeuristicJudge, LLMJudge  # noqa: PLC0415

    judge: Any
    if llm_judge:
        judge = LLMJudge()
        judge_name = "llm"
    else:
        judge = HeuristicJudge()
        judge_name = "heuristic"

    run_id = uuid.uuid4().hex[:12]
    total = len(prompts) * len(strategies)

    print(f"\n  run_id:     {run_id}")
    print(f"  prompts:    {len(prompts)}")
    print(f"  strategies: {strategies}")
    print(f"  judge:      {judge_name}")
    print(f"  total runs: {total}")
    print(f"  output:     {out_path}\n")

    if dry_run:
        print("  [dry-run] Stopping before API calls.\n")
        return []

    sem = asyncio.Semaphore(concurrency)
    records: List[Dict[str, Any]] = []

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        completed = 0
        for prompt in prompts:
            if verbose:
                print(
                f"\n  {prompt['id']} [{prompt['category']}] difficulty={prompt['difficulty']}"
            )
                print(
                    f"  {prompt['prompt'][:80]}{'...' if len(prompt['prompt']) > 80 else ''}"
                )

            tasks = [
                run_one(
                    prompt,
                    strategy,
                    judge=judge,
                    judge_name=judge_name,
                    dispatcher=dispatcher,
                    timeout_ms=timeout_ms,
                    run_id=run_id,
                    concurrency_sem=sem,
                    verbose=verbose,
                )
                for strategy in strategies
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, Exception):
                    print(f"  [error] {r}")
                    continue
                records.append(r)
                f.write(json.dumps(r) + "\n")
                f.flush()

            completed += len(strategies)
            if not verbose:
                pct = 100 * completed / total
                bar_len = 30
                filled = int(pct / 100 * bar_len)
                bar = "█" * filled + "░" * (bar_len - filled)
                print(
                    f"\r  [{bar}] {pct:5.1f}%  {completed}/{total}", end="", flush=True
                )

    if not verbose:
        print()
    print(f"\n  Wrote {len(records)} records to {out_path}\n")
    return records


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Goblin intelligence layer benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=ALL_STRATEGIES,
        default=ALL_STRATEGIES,
        help="Which routing strategies to benchmark (default: all four)",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=ALL_CATEGORIES,
        default=None,
        help="Prompt categories to include (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of prompts to run (after category filter)",
    )
    parser.add_argument(
        "--llm-judge",
        action="store_true",
        help="Use an LLM to score answer quality (slower, costs money)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output JSONL path (default: results/run_<timestamp>.jsonl)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30_000,
        help="Per-request timeout in ms (default: 30000)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Max concurrent requests across all strategies (default: 3)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print result for each prompt as it completes",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the run plan without making any API calls",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print a comparison report after the run completes",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.out) if args.out else RESULTS_DIR / f"run_{ts}.jsonl"

    prompts = load_prompts(categories=args.categories, limit=args.limit)
    if not prompts:
        print("No prompts matched the given filters.")
        sys.exit(1)

    print(f"\n  Goblin Benchmark — {ts}")
    print("  " + "─" * 48)

    records = asyncio.run(
        run_benchmark(
            prompts,
            args.strategies,
            llm_judge=args.llm_judge,
            out_path=out_path,
            timeout_ms=args.timeout,
            concurrency=args.concurrency,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
    )

    if args.report and records:
        from benchmarks.report import aggregate, print_summary, write_markdown  # noqa: PLC0415

        agg = aggregate(records)
        print_summary(agg)
        md_path = out_path.with_suffix(".md")
        write_markdown(agg, md_path)
        print(f"  Markdown report: {md_path}\n")


if __name__ == "__main__":
    main()
