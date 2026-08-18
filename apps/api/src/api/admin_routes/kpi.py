"""
KPI aggregation endpoint — /admin/kpi

Aggregates across four domains:
  system    — request success/failure, latency percentiles
  economics — cost/request, tokens/request, provider spend breakdown
  product   — users, conversations, session length, memory facts
  ai        — provider health snapshot, benchmark scores if available
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Request

from ..ops.security import require_ops_access

logger = structlog.get_logger(__name__)

router = APIRouter()

_BENCH_RESULTS = Path(__file__).resolve().parents[5] / "benchmarks" / "results"
_MEM_RESULTS = Path(__file__).resolve().parents[5] / "benchmarks" / "memory" / "results"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pct(n: int, total: int) -> Optional[float]:
    return round(n / total * 100, 2) if total else None


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    return round(statistics.quantiles(sorted(values), n=100)[int(p) - 1], 1)


def _latest_jsonl(directory: Path) -> Optional[Path]:
    if not directory.exists():
        return None
    files = sorted(directory.glob("*.jsonl"), reverse=True)
    return files[0] if files else None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except Exception:
        pass
    return rows


# ---------------------------------------------------------------------------
# System metrics — from task store (chat.completion tasks)
# ---------------------------------------------------------------------------


async def _system_metrics(since: datetime) -> Dict[str, Any]:
    from ..storage.tasks import task_store  # noqa: PLC0415

    tasks = await task_store.list_tasks(limit=2000)
    completions = [
        t
        for t in tasks
        if t.get("task_type") == "chat.completion"
        and _parse_ts(t.get("created_at")) >= since
    ]

    total = len(completions)
    successes = sum(1 for t in completions if t.get("status") == "completed")
    failures = total - successes

    latencies: List[float] = []
    for t in completions:
        result = t.get("result") or {}
        lat = result.get("latency_ms") or (t.get("metadata") or {}).get("latency_ms")
        if lat is not None:
            try:
                latencies.append(float(lat))
            except (TypeError, ValueError):
                pass

    return {
        "request_count": total,
        "success_count": successes,
        "failure_count": failures,
        "success_pct": _pct(successes, total),
        "failure_pct": _pct(failures, total),
        "p50_latency_ms": _percentile(latencies, 50),
        "p95_latency_ms": _percentile(latencies, 95),
        # Not yet instrumented — require streaming TTFT capture
        "ttft_ms": None,
        "tool_success_pct": None,
        "retrieval_latency_ms": None,
    }


# ---------------------------------------------------------------------------
# Economics metrics
# ---------------------------------------------------------------------------


async def _economics_metrics(since: datetime) -> Dict[str, Any]:
    from ..storage.tasks import task_store  # noqa: PLC0415
    from ..storage.usage_events import usage_event_store  # noqa: PLC0415

    tasks = await task_store.list_tasks(limit=2000)
    completions = [
        t
        for t in tasks
        if t.get("task_type") == "chat.completion"
        and _parse_ts(t.get("created_at")) >= since
    ]

    total = len(completions)
    total_cost = 0.0
    total_tokens = 0
    provider_spend: Dict[str, Dict[str, Any]] = {}

    for t in completions:
        result = t.get("result") or {}
        cost = float(result.get("cost_usd") or 0.0)
        usage = result.get("usage") or {}
        tokens = int(usage.get("total_tokens") or 0)
        provider = str(result.get("selected_provider") or "unknown")
        model = str(result.get("model") or "unknown")

        total_cost += cost
        total_tokens += tokens

        key = f"{provider}/{model}"
        if key not in provider_spend:
            provider_spend[key] = {
                "provider": provider,
                "model": model,
                "requests": 0,
                "cost_usd": 0.0,
                "tokens": 0,
            }
        provider_spend[key]["requests"] += 1
        provider_spend[key]["cost_usd"] += cost
        provider_spend[key]["tokens"] += tokens

    # Supplement with in-memory usage event store for any events not in tasks
    model_rollup = await usage_event_store.get_model_rollup(limit=50)

    breakdown = sorted(
        provider_spend.values(), key=lambda x: x["cost_usd"], reverse=True
    )
    for row in breakdown:
        row["cost_usd"] = round(row["cost_usd"], 6)

    return {
        "total_requests": total,
        "total_cost_usd": round(total_cost, 6),
        "cost_per_request_usd": round(total_cost / total, 6) if total else None,
        "tokens_per_request": round(total_tokens / total) if total else None,
        "total_tokens": total_tokens,
        "provider_breakdown": breakdown,
        "model_rollup": model_rollup[:20],
        # Routing savings require a cheapest-model baseline run — see benchmarks/
        "savings_from_routing_usd": None,
    }


# ---------------------------------------------------------------------------
# Product metrics — DB queries
# ---------------------------------------------------------------------------


async def _product_metrics(since: datetime) -> Dict[str, Any]:
    try:
        from sqlalchemy import func, select  # noqa: PLC0415

        from ..storage.database import get_db_context  # noqa: PLC0415
        from ..storage.models import ConversationModel, MessageModel, UserModel  # noqa: PLC0415
        from ..storage.vector_models import MemoryFactModel  # noqa: PLC0415

        since_naive = since.replace(tzinfo=None)

        async with get_db_context() as session:
            # Total users
            total_users = (
                await session.execute(
                    select(func.count())
                    .select_from(UserModel)
                    .where(UserModel.is_active == True)  # noqa: E712
                )
            ).scalar_one()

            # New users in window
            new_users = (
                await session.execute(
                    select(func.count())
                    .select_from(UserModel)
                    .where(
                        UserModel.created_at >= since_naive,
                        UserModel.is_active == True,  # noqa: E712
                    )
                )
            ).scalar_one()

            # Returning users: active before window start AND had a conversation in window
            returning_users = (
                await session.execute(
                    select(func.count(func.distinct(ConversationModel.user_id))).where(
                        ConversationModel.created_at >= since_naive,
                        ConversationModel.user_id.isnot(None),
                    )
                )
            ).scalar_one()

            # Total conversations
            total_convs = (
                await session.execute(
                    select(func.count()).select_from(ConversationModel)
                )
            ).scalar_one()

            # Conversations in window
            recent_convs = (
                await session.execute(
                    select(func.count())
                    .select_from(ConversationModel)
                    .where(ConversationModel.created_at >= since_naive)
                )
            ).scalar_one()

            # Average messages per conversation (session length)
            msg_per_conv = (
                await session.execute(
                    select(
                        func.count(MessageModel.message_id),
                        func.count(func.distinct(MessageModel.conversation_id)),
                    )
                )
            ).one()
            total_messages = int(msg_per_conv[0] or 0)
            total_conv_with_msgs = int(msg_per_conv[1] or 0)
            avg_session_turns = (
                round(total_messages / total_conv_with_msgs, 1)
                if total_conv_with_msgs
                else None
            )

            # Total memory facts
            total_memory_facts = (
                await session.execute(select(func.count()).select_from(MemoryFactModel))
            ).scalar_one()

        return {
            "total_users": int(total_users),
            "new_users_in_window": int(new_users),
            "returning_users_in_window": int(returning_users),
            "total_conversations": int(total_convs),
            "conversations_in_window": int(recent_convs),
            "total_messages": total_messages,
            "avg_session_turns": avg_session_turns,
            "total_memory_facts": int(total_memory_facts),
            # Goblin persona count requires the goblin entity — see api_router
            "goblins_created": None,
        }
    except Exception as exc:
        logger.warning("kpi_product_metrics_failed", error=str(exc))
        return {
            "total_users": None,
            "new_users_in_window": None,
            "returning_users_in_window": None,
            "total_conversations": None,
            "conversations_in_window": None,
            "total_messages": None,
            "avg_session_turns": None,
            "total_memory_facts": None,
            "goblins_created": None,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# AI metrics — provider snapshot + latest benchmark results
# ---------------------------------------------------------------------------


async def _ai_metrics() -> Dict[str, Any]:
    from ..providers.dispatcher import dispatcher  # noqa: PLC0415

    debug = dispatcher.debug_info()
    routing_table = debug.get("routing_table", [])

    provider_summary = {
        "total": len(routing_table),
        "configured": sum(1 for p in routing_table if p.get("configured")),
        "routing": sum(1 for p in routing_table if p.get("can_route", False)),
        "open_circuits": sum(
            1
            for p in routing_table
            if str((p.get("circuit_breaker") or {}).get("state", "")).lower()
            in {"soft_open", "hard_open"}
        ),
    }

    # Intelligence benchmark scores (latest JSONL if exists)
    intel_score: Optional[Dict[str, Any]] = None
    intel_path = _latest_jsonl(_BENCH_RESULTS)
    if intel_path:
        rows = _read_jsonl(intel_path)
        goblin_rows = [
            r for r in rows if r.get("strategy") == "goblin" and r.get("success")
        ]
        cheapest_rows = [
            r for r in rows if r.get("strategy") == "cheapest" and r.get("success")
        ]
        strongest_rows = [
            r for r in rows if r.get("strategy") == "strongest" and r.get("success")
        ]

        def _avg_quality(rs: List[Dict]) -> Optional[float]:
            vals = [
                r["quality_score"] for r in rs if r.get("quality_score") is not None
            ]
            return round(sum(vals) / len(vals), 3) if vals else None

        def _avg_cost(rs: List[Dict]) -> Optional[float]:
            vals = [r["cost_usd"] for r in rs if r.get("cost_usd") is not None]
            return round(sum(vals) / len(vals), 6) if vals else None

        g_quality = _avg_quality(goblin_rows)
        s_quality = _avg_quality(strongest_rows)
        intel_score = {
            "run_id": rows[0].get("run_id") if rows else None,
            "total_prompts": len(set(r.get("prompt_id") for r in rows)),
            "goblin_quality": g_quality,
            "cheapest_quality": _avg_quality(cheapest_rows),
            "strongest_quality": s_quality,
            "goblin_cost_per_request": _avg_cost(goblin_rows),
            "cheapest_cost_per_request": _avg_cost(cheapest_rows),
            "strongest_cost_per_request": _avg_cost(strongest_rows),
            "router_win_rate": (
                round(
                    sum(
                        1
                        for g, s in zip(goblin_rows, strongest_rows)
                        if (g.get("quality_score") or 0)
                        >= (s.get("quality_score") or 0) - 0.05
                    )
                    / max(min(len(goblin_rows), len(strongest_rows)), 1),
                    3,
                )
                if goblin_rows and strongest_rows
                else None
            ),
        }

    # Memory benchmark scores (latest JSONL if exists)
    mem_score: Optional[Dict[str, Any]] = None
    mem_path = _latest_jsonl(_MEM_RESULTS)
    if mem_path:
        rows = _read_jsonl(mem_path)
        if rows:
            scores = [
                r["memory_score"] for r in rows if r.get("memory_score") is not None
            ]
            recalls = [r["recall"] for r in rows if r.get("recall") is not None]
            relevances = [
                r["relevance"] for r in rows if r.get("relevance") is not None
            ]
            mem_score = {
                "run_id": rows[0].get("run_id"),
                "query_count": len(rows),
                "avg_memory_score": round(sum(scores) / len(scores), 3)
                if scores
                else None,
                "avg_recall": round(sum(recalls) / len(recalls), 3)
                if recalls
                else None,
                "avg_relevance": round(sum(relevances) / len(relevances), 3)
                if relevances
                else None,
            }

    return {
        "providers": provider_summary,
        "intelligence_benchmark": intel_score,
        "memory_benchmark": mem_score,
        # Tool-selection accuracy requires eval harness — not yet instrumented
        "tool_selection_accuracy": None,
    }


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------


def _parse_ts(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=timezone.utc) if raw.tzinfo is None else raw
    if isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("/kpi", include_in_schema=False)
@require_ops_access("read")
async def get_kpi(request: Request, days: int = 7) -> Dict[str, Any]:
    """Aggregated product KPIs across system, economics, product, and AI dimensions."""
    _ = request
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail="days must be 1–365")

    since = datetime.now(timezone.utc) - timedelta(days=days)

    system, economics, product, ai = await _gather(since)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": days,
        "since": since.isoformat(),
        "system": system,
        "economics": economics,
        "product": product,
        "ai": ai,
    }


async def _gather(since: datetime):
    import asyncio  # noqa: PLC0415

    return await asyncio.gather(
        _system_metrics(since),
        _economics_metrics(since),
        _product_metrics(since),
        _ai_metrics(),
        return_exceptions=False,
    )


__all__ = ["router"]
