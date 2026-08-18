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
from pydantic import BaseModel, Field

from ..ops.security import require_ops_access
from ..observability.retrieval_tracer import retrieval_tracer
from ..observability.tool_tracer import tool_tracer
from ..storage.tasks import task_store

logger = structlog.get_logger(__name__)

router = APIRouter()

_BENCH_RESULTS = Path(__file__).resolve().parents[5] / "benchmarks" / "results"
_MEM_RESULTS = Path(__file__).resolve().parents[5] / "benchmarks" / "memory" / "results"
_DOGFOOD_TASK_TYPE = "dogfood.external_ai"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pct(n: int, total: int) -> Optional[float]:
    return round(n / total * 100, 2) if total else None


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 1)
    try:
        return round(statistics.quantiles(ordered, n=100)[int(p) - 1], 1)
    except statistics.StatisticsError:
        return round(ordered[-1], 1)


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


def _recent_tasks_by_type(tasks: List[Dict[str, Any]], task_type: str) -> List[Dict[str, Any]]:
    entries = [
        task
        for task in tasks
        if str(task.get("task_type") or "") == task_type
    ]
    entries.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return entries


class DogfoodLogEntry(BaseModel):
    entry_id: str
    primary_assistant: str
    external_ai: str
    reason: str
    context: Optional[str] = None
    recorded_at: str
    source: str = "dashboard"


class DogfoodLogInput(BaseModel):
    primary_assistant: str = Field(min_length=1, max_length=64)
    external_ai: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=500)
    context: Optional[str] = Field(default=None, max_length=1000)


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
    fallback_count = 0
    ttft_values: List[float] = []
    retrieval_latencies: List[float] = []
    for t in completions:
        result = t.get("result") or {}
        lat = result.get("latency_ms") or (t.get("metadata") or {}).get("latency_ms")
        if lat is not None:
            try:
                latencies.append(float(lat))
            except (TypeError, ValueError):
                pass
        if result.get("used_fallback") or (t.get("metadata") or {}).get("used_fallback"):
            fallback_count += 1
        ttft = result.get("ttft_ms") or (t.get("metadata") or {}).get("ttft_ms")
        if ttft is not None:
            try:
                ttft_values.append(float(ttft))
            except (TypeError, ValueError):
                pass
        retrieval = result.get("retrieval_latency_ms") or (t.get("metadata") or {}).get(
            "retrieval_latency_ms"
        )
        if retrieval is not None:
            try:
                retrieval_latencies.append(float(retrieval))
            except (TypeError, ValueError):
                pass

    window_hours = max(
        1, int((datetime.now(timezone.utc) - since).total_seconds() // 3600)
    )

    retrieval_history_latencies: List[float] = []
    try:
        history = await retrieval_tracer.get_retrieval_history(limit=200)
        for trace in history:
            latency = trace.get("retrieval_time_ms")
            if latency is not None:
                retrieval_history_latencies.append(float(latency))
    except Exception:
        pass

    try:
        tool_stats = tool_tracer.get_tool_trace_stats(time_window_hours=window_hours)
    except Exception:
        tool_stats = {}
    tool_stats_data = tool_stats.get("stats") if isinstance(tool_stats, dict) else None
    tool_success_pct = (
        round(float(tool_stats_data.get("avg_success_rate", 0.0)) * 100, 2)
        if tool_stats_data
        else _pct(
            sum(1 for t in completions if (t.get("result") or {}).get("tool_success") is True),
            total,
        )
    )

    dogfood_entries = _recent_tasks_by_type(tasks, _DOGFOOD_TASK_TYPE)
    fallback_pct = _pct(fallback_count, total)
    provider_failure_pct = _pct(failures, total)
    combined_retrieval_latencies = retrieval_history_latencies or retrieval_latencies

    return {
        "request_count": total,
        "success_count": successes,
        "failure_count": failures,
        "success_pct": _pct(successes, total),
        "failure_pct": provider_failure_pct,
        "provider_failure_pct": provider_failure_pct,
        "fallback_pct": fallback_pct,
        "p50_latency_ms": _percentile(latencies, 50),
        "p95_latency_ms": _percentile(latencies, 95),
        "ttft_ms": _percentile(ttft_values, 50),
        "tool_success_pct": tool_success_pct,
        "retrieval_latency_ms": _percentile(combined_retrieval_latencies, 50),
        "dogfood": {
            "total_entries": len(dogfood_entries),
            "recent_entries": [
                _dogfood_entry_from_task(task) for task in dogfood_entries[:8]
            ],
            "reason_counts": _dogfood_reason_counts(dogfood_entries),
        },
    }


# ---------------------------------------------------------------------------
# Economics metrics
# ---------------------------------------------------------------------------


async def _economics_metrics(since: datetime, window_days: int) -> Dict[str, Any]:
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
    unique_users = set()

    for t in completions:
        result = t.get("result") or {}
        cost = float(result.get("cost_usd") or 0.0)
        usage = result.get("usage") or {}
        tokens = int(usage.get("total_tokens") or 0)
        provider = str(result.get("selected_provider") or "unknown")
        model = str(result.get("model") or "unknown")
        user_id = str(t.get("user_id") or "")

        total_cost += cost
        total_tokens += tokens
        if user_id:
            unique_users.add(user_id)

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
    routing_savings_usd: Optional[float] = None
    benchmark_path = _latest_jsonl(_BENCH_RESULTS)
    if benchmark_path:
        benchmark_rows = _read_jsonl(benchmark_path)
        routing_savings_usd = _benchmark_routing_savings(benchmark_rows)

    breakdown = sorted(
        provider_spend.values(), key=lambda x: x["cost_usd"], reverse=True
    )
    for row in breakdown:
        row["cost_usd"] = round(row["cost_usd"], 6)

    return {
        "total_requests": total,
        "total_cost_usd": round(total_cost, 6),
        "cost_per_request_usd": round(total_cost / total, 6) if total else None,
        "cost_per_user_day_usd": round(
            total_cost / max(len(unique_users) * max(window_days, 1), 1),
            6,
        )
        if total
        else None,
        "tokens_per_request": round(total_tokens / total) if total else None,
        "total_tokens": total_tokens,
        "provider_breakdown": breakdown,
        "model_rollup": model_rollup[:20],
        "savings_from_routing_usd": routing_savings_usd,
    }


# ---------------------------------------------------------------------------
# Product metrics — DB queries
# ---------------------------------------------------------------------------


async def _product_metrics(since: datetime) -> Dict[str, Any]:
    try:
        from sqlalchemy import desc, func, select  # noqa: PLC0415

        from ..storage.database import get_db_context  # noqa: PLC0415
        from ..storage.models import (  # noqa: PLC0415
            ConversationModel,
            MessageModel,
            SupportTicketModel,
            UserModel,
        )
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

            # Returning users: users with at least one conversation before the
            # window and another conversation inside the window.
            returning_users = (
                await session.execute(
                    select(func.count(func.distinct(ConversationModel.user_id))).where(
                        ConversationModel.user_id.isnot(None),
                        ConversationModel.user_id.in_(
                            select(func.distinct(ConversationModel.user_id)).where(
                                ConversationModel.created_at < since_naive,
                                ConversationModel.user_id.isnot(None),
                            )
                        ),
                        ConversationModel.user_id.in_(
                            select(func.distinct(ConversationModel.user_id)).where(
                                ConversationModel.created_at >= since_naive,
                                ConversationModel.user_id.isnot(None),
                            )
                        ),
                    )
                )
            ).scalar_one()

            # Total conversations
            total_convs = (
                await session.execute(
                    select(func.count()).select_from(ConversationModel)
                )
            ).scalar_one()
            chats_per_user = round(int(total_convs) / int(total_users), 2) if total_users else None

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

            try:
                from ..api_router import get_goblins  # noqa: PLC0415

                goblins_created = len(await get_goblins())
            except Exception:
                goblins_created = None

            recent_messages = (
                await session.execute(
                    select(MessageModel.role, MessageModel.metadata_).where(
                        MessageModel.timestamp >= since_naive
                    )
                )
            ).all()
            feature_usage: Dict[str, int] = {
                "attachments_used": 0,
                "context_assembly_enabled": 0,
                "language_detection": 0,
                "wti_enriched": 0,
                "intent_enriched": 0,
            }
            conversation_categories: Dict[str, int] = {}
            for role, metadata in recent_messages:
                if role != "user":
                    continue
                md = metadata or {}
                if md.get("attachments"):
                    feature_usage["attachments_used"] += 1
                if md.get("context_assembly_enabled"):
                    feature_usage["context_assembly_enabled"] += 1
                if md.get("language_detected"):
                    feature_usage["language_detection"] += 1
                if md.get("write_time_execution"):
                    feature_usage["wti_enriched"] += 1
                if md.get("intent"):
                    feature_usage["intent_enriched"] += 1
                category = md.get("conversation_category")
                if category:
                    key = str(category)
                    conversation_categories[key] = conversation_categories.get(key, 0) + 1

            beta_signal_rows = (
                await session.execute(
                    select(SupportTicketModel)
                    .where(
                        SupportTicketModel.created_at >= since_naive,
                        SupportTicketModel.category == "beta_signal",
                    )
                    .order_by(desc(SupportTicketModel.created_at))
                    .limit(20)
                )
            ).scalars().all()
            pilot_tags: Dict[str, int] = {}
            pilot_participants: Dict[str, int] = {}
            recent_pilot_signals = []
            for ticket in beta_signal_rows:
                metadata = ticket.metadata_ or {}
                tag = str(metadata.get("tag") or metadata.get("page") or "uncategorized")
                pilot_tags[tag] = pilot_tags.get(tag, 0) + 1
                participant_key = str(
                    ticket.email
                    or metadata.get("email")
                    or metadata.get("name")
                    or "anonymous"
                ).strip().lower()
                pilot_participants[participant_key] = pilot_participants.get(participant_key, 0) + 1
                recent_pilot_signals.append(
                    {
                        "ticket_id": ticket.ticket_id,
                        "page": metadata.get("page"),
                        "tag": metadata.get("tag"),
                        "name": metadata.get("name") or ticket.email,
                        "email": ticket.email or metadata.get("email"),
                        "note": ticket.message,
                        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                    }
                )

        return {
            "total_users": int(total_users),
            "new_users_in_window": int(new_users),
            "returning_users_in_window": int(returning_users),
            "total_conversations": int(total_convs),
            "conversations_in_window": int(recent_convs),
            "chats_per_user": chats_per_user,
            "total_messages": total_messages,
            "avg_session_turns": avg_session_turns,
            "total_memory_facts": int(total_memory_facts),
            "goblins_created": goblins_created,
            "feature_usage": {
                "counts": feature_usage,
                "conversation_categories": dict(
                    sorted(
                        conversation_categories.items(),
                        key=lambda item: (-item[1], item[0]),
                        )[:8]
                ),
            },
            "pilot_signals": {
                "total_signals": len(beta_signal_rows),
                "unique_participants": len(pilot_participants),
                "top_tags": [
                    {"tag": tag, "count": count}
                    for tag, count in sorted(
                        pilot_tags.items(), key=lambda item: (-item[1], item[0])
                    )[:5]
                ],
                "recent_signals": recent_pilot_signals,
            },
        }
    except Exception as exc:
        logger.warning("kpi_product_metrics_failed", error=str(exc))
        return {
            "total_users": None,
            "new_users_in_window": None,
            "returning_users_in_window": None,
            "total_conversations": None,
            "conversations_in_window": None,
            "chats_per_user": None,
            "total_messages": None,
            "avg_session_turns": None,
            "total_memory_facts": None,
            "goblins_created": None,
            "feature_usage": None,
            "pilot_signals": None,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# AI metrics — provider snapshot + latest benchmark results
# ---------------------------------------------------------------------------


async def _ai_metrics(window_hours: int) -> Dict[str, Any]:
    from ..providers.dispatcher import dispatcher  # noqa: PLC0415

    debug = dispatcher.debug_info()
    routing_table = debug.get("routing_table", [])

    try:
        tool_stats = tool_tracer.get_tool_trace_stats(time_window_hours=window_hours)
    except Exception:
        tool_stats = {}
    tool_stats_data = tool_stats.get("stats") if isinstance(tool_stats, dict) else None
    tool_selection_accuracy = (
        round(float(tool_stats_data.get("avg_success_rate", 0.0)) * 100, 2)
        if tool_stats_data
        else None
    )

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
    provider_model_evals: List[Dict[str, Any]] = []
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
        provider_model_evals = _benchmark_provider_model_evals(rows)

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
        "provider_model_evals": provider_model_evals,
        "tool_selection_accuracy": tool_selection_accuracy,
    }


def _dogfood_entry_from_task(task: Dict[str, Any]) -> Dict[str, Any]:
    payload = task.get("payload") or {}
    result = task.get("result") or {}
    metadata = task.get("metadata") or {}
    return {
        "entry_id": str(task.get("task_id") or ""),
        "primary_assistant": str(payload.get("primary_assistant") or result.get("primary_assistant") or "Goblin"),
        "external_ai": str(payload.get("external_ai") or result.get("external_ai") or "other"),
        "reason": str(payload.get("reason") or result.get("reason") or payload.get("task") or ""),
        "context": payload.get("context") or result.get("context") or metadata.get("context"),
        "recorded_at": str(task.get("created_at") or ""),
        "source": str(metadata.get("source") or payload.get("source") or "dashboard"),
    }


def _dogfood_reason_counts(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for task in tasks:
        entry = _dogfood_entry_from_task(task)
        key = entry["reason"].strip().lower() or "unspecified"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10])


def _benchmark_provider_model_evals(
    rows: List[Dict[str, Any]], limit: int = 8
) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        provider = str(row.get("selected_provider") or "").strip()
        model = str(row.get("selected_model") or "").strip()
        if not provider or not model:
            continue
        bucket = grouped.setdefault(
            (provider, model),
            {
                "provider": provider,
                "model": model,
                "sample_count": 0,
                "success_count": 0,
                "fallback_count": 0,
                "quality_scores": [],
                "costs": [],
                "ttfts": [],
            },
        )
        bucket["sample_count"] += 1
        bucket["success_count"] += 1 if row.get("success") else 0
        bucket["fallback_count"] += 1 if row.get("used_fallback") else 0
        if row.get("quality_score") is not None:
            bucket["quality_scores"].append(float(row["quality_score"]))
        if row.get("cost_usd") is not None:
            bucket["costs"].append(float(row["cost_usd"]))
        if row.get("ttft_ms") is not None:
            bucket["ttfts"].append(float(row["ttft_ms"]))

    evals: List[Dict[str, Any]] = []
    for bucket in grouped.values():
        sample_count = bucket["sample_count"]
        evals.append(
            {
                "provider": bucket["provider"],
                "model": bucket["model"],
                "sample_count": sample_count,
                "success_rate": round(bucket["success_count"] / sample_count, 3)
                if sample_count
                else None,
                "fallback_rate": round(bucket["fallback_count"] / sample_count, 3)
                if sample_count
                else None,
                "avg_quality_score": round(
                    sum(bucket["quality_scores"]) / len(bucket["quality_scores"]), 3
                )
                if bucket["quality_scores"]
                else None,
                "avg_cost_usd": round(sum(bucket["costs"]) / len(bucket["costs"]), 6)
                if bucket["costs"]
                else None,
                "avg_ttft_ms": round(sum(bucket["ttfts"]) / len(bucket["ttfts"]), 1)
                if bucket["ttfts"]
                else None,
            }
        )

    evals.sort(
        key=lambda item: (
            -(item["avg_quality_score"] or -1.0),
            -(item["sample_count"] or 0),
            item["provider"],
            item["model"],
        )
    )
    return evals[:limit]


def _benchmark_routing_savings(rows: List[Dict[str, Any]]) -> Optional[float]:
    """
    Estimate routing savings by pairing Goblin and strongest strategy runs.

    Only successful runs with concrete costs are included. This keeps the
    metric conservative and directly comparable to the report verdict.
    """

    paired: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in rows:
        prompt_id = str(row.get("prompt_id") or "").strip()
        strategy = str(row.get("strategy") or "").strip()
        if not prompt_id or strategy not in {"goblin", "strongest"}:
            continue
        paired.setdefault(prompt_id, {})[strategy] = row

    savings = 0.0
    pair_count = 0
    for prompt_rows in paired.values():
        goblin = prompt_rows.get("goblin")
        strongest = prompt_rows.get("strongest")
        if not goblin or not strongest:
            continue
        if not goblin.get("success") or not strongest.get("success"):
            continue
        g_cost = goblin.get("cost_usd")
        s_cost = strongest.get("cost_usd")
        if g_cost is None or s_cost is None:
            continue
        try:
            savings += float(s_cost) - float(g_cost)
            pair_count += 1
        except (TypeError, ValueError):
            continue

    return round(savings, 6) if pair_count else None


@router.get("/kpi/dogfood", include_in_schema=False)
@require_ops_access("read")
async def get_dogfood_log(request: Request, limit: int = 25) -> Dict[str, Any]:
    _ = request
    tasks = await task_store.list_tasks(limit=max(50, limit * 4))
    entries = _recent_tasks_by_type(tasks, _DOGFOOD_TASK_TYPE)
    dogfood_entries = [_dogfood_entry_from_task(task) for task in entries[:limit]]
    return {
        "success": True,
        "data": {
            "total_entries": len(entries),
            "recent_entries": dogfood_entries,
            "reason_counts": _dogfood_reason_counts(entries),
        },
    }


@router.post("/kpi/dogfood", include_in_schema=False)
@require_ops_access("write")
async def record_dogfood_entry(request: Request, payload: DogfoodLogInput) -> Dict[str, Any]:
    _ = request
    entry_id = (
        f"dogfood-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        f"-{payload.external_ai.lower().replace(' ', '-')}"
    )
    await task_store.save_task(
        entry_id,
        {
            "task_id": entry_id,
            "user_id": "ops",
            "status": "completed",
            "task_type": _DOGFOOD_TASK_TYPE,
            "payload": {
                "primary_assistant": payload.primary_assistant,
                "external_ai": payload.external_ai,
                "reason": payload.reason,
                "context": payload.context,
                "source": "dashboard",
            },
            "result": {
                "primary_assistant": payload.primary_assistant,
                "external_ai": payload.external_ai,
                "reason": payload.reason,
                "context": payload.context,
            },
            "metadata": {
                "source": "dashboard",
                "kind": "dogfood_note",
            },
        },
    )
    return {
        "success": True,
        "data": _dogfood_entry_from_task(await task_store.get_task(entry_id) or {}),
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

    window_hours = max(1, int((datetime.now(timezone.utc) - since).total_seconds() // 3600))
    return await asyncio.gather(
        _system_metrics(since),
        _economics_metrics(since, max(int((datetime.now(timezone.utc) - since).days), 1)),
        _product_metrics(since),
        _ai_metrics(window_hours),
        return_exceptions=False,
    )


__all__ = ["router"]
