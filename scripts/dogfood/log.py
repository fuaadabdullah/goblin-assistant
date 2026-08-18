#!/usr/bin/env python3
"""
Goblin dogfood failure logger.

Log when you reach for another AI instead of Goblin:

  gfail web-research "needed current prices"
  gfail memory-miss
  gfail                          # interactive prompt

Report:
  gfail --report
  gfail --report --days 14

Categories:
  web-research     Needed deeper / real-time web search
  tool-exec        Tool execution was broken or annoying
  memory-miss      Memory failed to recall something relevant
  too-slow         Response was unacceptably slow
  coding-context   Coding context was insufficient
  ui-friction      UI friction made it easier to go elsewhere
  model-selection  Wrong model picked; no good override
  file-support     Needed to upload / reference a file
  image-support    Needed image understanding
  other            Anything else
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVENTS_DIR = HERE / "events"

CATEGORIES: dict[str, str] = {
    "web-research": "Needed deeper / real-time web search",
    "tool-exec": "Tool execution was broken or annoying",
    "memory-miss": "Memory failed to recall something relevant",
    "too-slow": "Response was unacceptably slow",
    "coding-context": "Coding context was insufficient",
    "ui-friction": "UI friction made it easier to go elsewhere",
    "model-selection": "Wrong model picked; no good override",
    "file-support": "Needed to upload / reference a file",
    "image-support": "Needed image understanding",
    "other": "Anything else",
}

SHORT: dict[str, str] = {
    "web": "web-research",
    "mem": "memory-miss",
    "slow": "too-slow",
    "code": "coding-context",
    "ui": "ui-friction",
    "model": "model-selection",
    "file": "file-support",
    "image": "image-support",
    "tool": "tool-exec",
}


def _week_path(ts: datetime) -> Path:
    iso = ts.isocalendar()
    return EVENTS_DIR / f"events_{iso.year}-W{iso.week:02d}.jsonl"


def _resolve_category(raw: str) -> str:
    key = raw.strip().lower()
    if key in CATEGORIES:
        return key
    if key in SHORT:
        return SHORT[key]
    # number shorthand
    keys = list(CATEGORIES)
    if key.isdigit():
        idx = int(key) - 1
        if 0 <= idx < len(keys):
            return keys[idx]
    # prefix match
    matches = [c for c in CATEGORIES if c.startswith(key)]
    if len(matches) == 1:
        return matches[0]
    print(f"Unknown category '{raw}'. Available:\n")
    for i, (k, v) in enumerate(CATEGORIES.items(), 1):
        print(f"  {i:2}.  {k:<18} {v}")
    sys.exit(1)


def _prompt_category() -> str:
    print("\nWhy did you leave Goblin?\n")
    keys = list(CATEGORIES)
    for i, k in enumerate(keys, 1):
        print(f"  {i:2}.  {k:<18} {CATEGORIES[k]}")
    print()
    raw = input("Category (name, shorthand, or number): ").strip()
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(keys):
            return keys[idx]
        print("Out of range.")
        sys.exit(1)
    return _resolve_category(raw)


def log_event(category: str, note: str) -> None:
    ts = datetime.now(timezone.utc)
    record = {
        "ts": ts.isoformat(),
        "category": category,
        "note": note,
    }
    path = _week_path(ts)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
    label = CATEGORIES[category]
    print(f"Logged: [{category}] {note or label}")


def _load_events(days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = []
    for path in sorted(EVENTS_DIR.glob("events_*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts = datetime.fromisoformat(rec["ts"])
                    if ts >= cutoff:
                        events.append(rec)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
    return events


def _bar(n: int, total: int, width: int = 24) -> str:
    filled = int(round((n / max(total, 1)) * width))
    return "█" * filled + "░" * (width - filled)


def report(days: int) -> None:
    events = _load_events(days)
    if not events:
        print(
            f"No bail events in the last {days} days. Either Goblin is perfect or you forgot to log."
        )
        return

    total = len(events)
    counts: Counter = Counter(e["category"] for e in events)
    by_day: dict[str, list] = defaultdict(list)
    for e in events:
        day = e["ts"][:10]
        by_day[day].append(e)

    print(f"\n{'═' * 66}")
    print(f"  GOBLIN DOGFOOD REPORT  —  last {days} days  ({total} bail events)")
    print(f"{'═' * 66}\n")

    print(f"  {'Category':<20} {'Count':>5}  {'Bar':<26}  {'%':>5}")
    print("  " + "─" * 60)
    for cat, n in counts.most_common():
        pct = n / total * 100
        print(f"  {cat:<20} {n:>5}  [{_bar(n, total)}]  {pct:>4.0f}%")

    print(f"\n  Total: {total}  ·  avg {total / max(len(by_day), 1):.1f}/day")

    # Daily cadence
    print(f"\n{'─' * 66}")
    print("  DAILY CADENCE")
    print(f"{'─' * 66}")
    for day in sorted(by_day):
        day_events = by_day[day]
        cats = Counter(e["category"] for e in day_events)
        top = ", ".join(f"{k}×{v}" for k, v in cats.most_common(3))
        print(f"  {day}  {len(day_events):>3} bails   {top}")

    # Notes (non-empty)
    noted = [(e["category"], e["note"]) for e in events if e.get("note")]
    if noted:
        print(f"\n{'─' * 66}")
        print("  NOTES")
        print(f"{'─' * 66}")
        for cat, note in noted[-20:]:  # last 20
            print(f"  [{cat}] {note}")

    # Verdict
    print(f"\n{'─' * 66}")
    print("  PRODUCT SIGNAL")
    print(f"{'─' * 66}")
    top3 = counts.most_common(3)
    for rank, (cat, n) in enumerate(top3, 1):
        pct = n / total * 100
        desc = CATEGORIES.get(cat, cat)
        print(f"  #{rank}  {cat}  ({pct:.0f}%)  —  {desc}")
    if top3:
        top_cat = top3[0][0]
        print(f"\n  Primary blocker: {top_cat.upper()}")
        if top_cat == "web-research":
            print("  → Integrate a real-time search tool (Brave/Tavily/Exa).")
        elif top_cat == "memory-miss":
            print("  → Run the memory benchmark. Recall < 0.7 needs work.")
        elif top_cat == "too-slow":
            print("  → Check TTFT distribution in the intelligence benchmark.")
        elif top_cat == "tool-exec":
            print("  → File the specific friction as a UX blocker in rc/v1 scope.")
        elif top_cat == "coding-context":
            print("  → Consider deeper IDE integration or context window expansion.")
        elif top_cat == "ui-friction":
            print("  → Log the exact friction point as a UX blocker.")
        elif top_cat == "file-support":
            print("  → File upload support is a hard gap. Prioritize or document.")
        elif top_cat == "image-support":
            print("  → Multimodal input is not in rc/v1. Log as post-v1 backlog.")
    print(f"\n{'═' * 66}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Log why you bailed on Goblin and reached for another AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "category",
        nargs="?",
        help="Failure category (name, shorthand, or number). Omit for interactive.",
    )
    parser.add_argument(
        "note",
        nargs="?",
        default="",
        help="Optional one-line note about what specifically failed.",
    )
    parser.add_argument(
        "--report",
        "-r",
        action="store_true",
        help="Print a summary report instead of logging.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days of history for --report (default: 7).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all categories and exit.",
    )
    args = parser.parse_args()

    if args.list:
        for k, v in CATEGORIES.items():
            print(f"  {k:<18} {v}")
        return

    if args.report:
        report(args.days)
        return

    category = _resolve_category(args.category) if args.category else _prompt_category()

    note = args.note
    if not note and not args.category:
        note = input("Optional note (enter to skip): ").strip()

    log_event(category, note)


if __name__ == "__main__":
    main()
