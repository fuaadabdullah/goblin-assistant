#!/usr/bin/env python3
"""
cProfile snapshot of the pure hot paths.

Usage:
    python scripts/profile_hotpaths.py              # print top-20 by cumtime
    python scripts/profile_hotpaths.py --out /tmp/prof.stats   # also write .stats file
    python scripts/profile_hotpaths.py --top 40     # show more rows
    python scripts/profile_hotpaths.py --sort tottime

The script runs each workload N_ITER times so the numbers are stable.
No database, network, or AI provider is needed.
"""

import argparse
import cProfile
import pstats
import io
import random
import string
import sys
import os

# Add src to path so we can import the API package
_here = os.path.dirname(os.path.abspath(__file__))
_src = os.path.join(_here, "..", "src")
sys.path.insert(0, _src)

from api.services.retrieval_service._token_budget import (
    apply_context_token_budget,
    estimate_tokens,
    trim_item_to_token_budget,
)
from api.services.retrieval_service._context_bundle import build_context_bundle
from api.services.message_classifier import MessageClassifier
from api.utils.tokenizer import count_tokens, trim_to_tokens

N_ITER = 500

_classifier = MessageClassifier()

_SAMPLE_MESSAGES = [
    ("I am a senior data engineer with 8 years experience in Python and Spark.", "user"),
    ("What is the current VaR and Sharpe ratio for a 60/40 equity/bond portfolio?", "user"),
    ("How will the FOMC rate decision affect yield curve inversion and credit spreads?", "user"),
    ("I prefer functional programming. I dislike verbose Java-style OOP.", "user"),
    ("Done! The authentication middleware is implemented and all unit tests pass.", "assistant"),
    ("Can you explain duration and convexity for a CFA exam candidate?", "user"),
    ("ok", "user"),
    ("hey, what's up?", "user"),
]


def _random_text(n_words: int) -> str:
    words = [
        "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
        for _ in range(n_words)
    ]
    return " ".join(words)


def _make_item(n_words: int, source_type: str = "message") -> dict:
    return {
        "content": _random_text(n_words),
        "source_type": source_type,
        "score": random.random(),
        "metadata": {},
    }


def _build_realistic_items(n_each: int) -> list:
    source_types = ["message", "summary", "memory", "document", "task", "ephemeral"]
    items = []
    for st in source_types:
        for _ in range(n_each):
            items.append(_make_item(random.randint(20, 120), source_type=st))
    return items


def workload() -> None:
    """Single iteration of every hot path."""
    # --- token budget primitives ---
    for _ in range(10):
        estimate_tokens(_random_text(200))

    for _ in range(5):
        item = _make_item(200)
        trim_item_to_token_budget(item, 100)

    # --- full bundle pipeline ---
    items = _build_realistic_items(n_each=10)
    bundle_raw = {
        "memory_facts": [_make_item(80) for _ in range(5)],
        "summaries": [_make_item(120) for _ in range(5)],
        "documents": [_make_item(300) for _ in range(3)],
        "messages": [_make_item(60) for _ in range(30)],
        "ephemeral_messages": [_make_item(40) for _ in range(15)],
        "tasks": [_make_item(30) for _ in range(5)],
    }
    b = {k: list(v) for k, v in bundle_raw.items()}
    apply_context_token_budget(b, max_tokens=3000)

    build_context_bundle(
        query="summarise my risk exposure",
        user_id="user-profile",
        conversation_id="conv-profile",
        all_context=items,
        max_tokens=4000,
        degraded_status={"degraded_mode": False, "reason": None},
    )

    # --- message classifier ---
    for content, role in _SAMPLE_MESSAGES:
        _classifier.classify_message(content, role)

    # --- tokenizer ---
    for n in [50, 500, 2000]:
        text = _random_text(n)
        count_tokens(text)
        trim_to_tokens(text, n // 3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile goblin-assistant hot paths")
    parser.add_argument("--out", metavar="FILE", help="Write .stats file to this path")
    parser.add_argument("--top", type=int, default=20, metavar="N", help="Rows to print (default 20)")
    parser.add_argument(
        "--sort",
        default="cumtime",
        choices=["cumtime", "tottime", "calls", "pcalls"],
        help="Sort key (default: cumtime)",
    )
    args = parser.parse_args()

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(N_ITER):
        workload()
    profiler.disable()

    if args.out:
        profiler.dump_stats(args.out)
        print(f"Stats written to {args.out}")

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats(args.sort)
    stats.print_stats(args.top)

    output = stream.getvalue()
    # Strip the long absolute path prefix to keep the table readable
    short = output.replace(os.path.join(_src, "api"), "<api>")
    print(short)


if __name__ == "__main__":
    main()
