"""Persistent usage event store with per-day user aggregation."""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog

_log = structlog.get_logger()


class UsageEventStore:
    """Storage abstraction for usage events and daily rollups."""

    def __init__(self):
        self.use_db = os.getenv("USE_DATABASE", "false").lower() == "true"
        self._in_memory_events: List[Dict[str, Any]] = []
        self._in_memory_daily: Dict[Tuple[str, date], Dict[str, Any]] = {}

    async def save_event(self, event: Dict[str, Any]) -> str:
        """Persist a usage event and update daily aggregate."""
        normalized = self._normalize_event(event)
        event_id = normalized["event_id"]

        if self.use_db:
            await self._save_event_to_db(normalized)
        else:
            self._save_event_in_memory(normalized)
        return event_id

    async def get_daily_usage(
        self, user_id: str, usage_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Return aggregated usage for a user/day."""
        usage_date = usage_date or date.today()

        if self.use_db:
            return await self._get_daily_usage_from_db(user_id, usage_date)

        entry = self._in_memory_daily.get((user_id, usage_date))
        if not entry:
            return self._empty_daily_usage(user_id, usage_date)
        return dict(entry)

    async def check_limits(
        self,
        user_id: str,
        *,
        additional_tokens: int = 0,
        additional_cost_usd: float = 0.0,
    ) -> Dict[str, Any]:
        """Check whether today's user usage stays within configured daily limits."""
        token_limit = _parse_int_env("GOBLIN_DAILY_TOKEN_LIMIT", 0)
        cost_limit = _parse_float_env("GOBLIN_DAILY_COST_LIMIT_USD", 0.0)

        usage = await self.get_daily_usage(user_id)
        projected_tokens = int(usage.get("total_tokens", 0)) + max(0, int(additional_tokens))
        projected_cost = float(usage.get("total_cost_usd", 0.0)) + max(
            0.0, float(additional_cost_usd)
        )

        token_exceeded = token_limit > 0 and projected_tokens > token_limit
        cost_exceeded = cost_limit > 0 and projected_cost > cost_limit

        reason = None
        if token_exceeded:
            reason = "daily_token_limit_exceeded"
        elif cost_exceeded:
            reason = "daily_cost_limit_exceeded"

        return {
            "allowed": not (token_exceeded or cost_exceeded),
            "reason": reason,
            "usage": usage,
            "token_limit": token_limit,
            "cost_limit_usd": cost_limit,
            "projected_total_tokens": projected_tokens,
            "projected_total_cost_usd": projected_cost,
        }

    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        created_at = event.get("created_at")
        if isinstance(created_at, datetime):
            event_time = created_at
        elif isinstance(created_at, str):
            event_time = _parse_datetime(created_at)
        else:
            event_time = datetime.utcnow()

        prompt_tokens = int(event.get("prompt_tokens") or 0)
        completion_tokens = int(event.get("completion_tokens") or 0)
        total_tokens = int(event.get("total_tokens") or (prompt_tokens + completion_tokens))
        cost_usd = float(event.get("cost_usd") or 0.0)

        return {
            "event_id": str(event.get("event_id") or uuid.uuid4()),
            "user_id": str(event.get("user_id") or ""),
            "conversation_id": event.get("conversation_id"),
            "message_id": event.get("message_id"),
            "provider": event.get("provider"),
            "model": event.get("model"),
            "prompt_tokens": max(0, prompt_tokens),
            "completion_tokens": max(0, completion_tokens),
            "total_tokens": max(0, total_tokens),
            "cost_usd": max(0.0, cost_usd),
            "metadata": event.get("metadata") or {},
            "created_at": event_time,
            "usage_date": event_time.date(),
        }

    def _save_event_in_memory(self, event: Dict[str, Any]) -> None:
        self._in_memory_events.append(dict(event))
        key = (event["user_id"], event["usage_date"])
        aggregate = self._in_memory_daily.get(key)
        if not aggregate:
            aggregate = self._empty_daily_usage(event["user_id"], event["usage_date"])

        aggregate["event_count"] += 1
        aggregate["prompt_tokens"] += int(event["prompt_tokens"])
        aggregate["completion_tokens"] += int(event["completion_tokens"])
        aggregate["total_tokens"] += int(event["total_tokens"])
        aggregate["total_cost_usd"] += float(event["cost_usd"])
        aggregate["updated_at"] = datetime.utcnow().isoformat()

        self._in_memory_daily[key] = aggregate

    async def _save_event_to_db(self, event: Dict[str, Any]) -> None:
        try:
            from sqlalchemy import select

            from .database import get_db_context
            from .models import UsageDailyAggregateModel, UsageEventModel

            async with get_db_context() as session:
                session.add(
                    UsageEventModel(
                        event_id=event["event_id"],
                        user_id=event["user_id"],
                        conversation_id=event.get("conversation_id"),
                        message_id=event.get("message_id"),
                        provider=event.get("provider"),
                        model=event.get("model"),
                        prompt_tokens=event["prompt_tokens"],
                        completion_tokens=event["completion_tokens"],
                        total_tokens=event["total_tokens"],
                        cost_usd=event["cost_usd"],
                        metadata_=event.get("metadata") or {},
                        created_at=event["created_at"],
                    )
                )

                daily_q = await session.execute(
                    select(UsageDailyAggregateModel).where(
                        UsageDailyAggregateModel.user_id == event["user_id"],
                        UsageDailyAggregateModel.usage_date == event["usage_date"],
                    )
                )
                daily = daily_q.scalar_one_or_none()
                if daily is None:
                    daily = UsageDailyAggregateModel(
                        user_id=event["user_id"],
                        usage_date=event["usage_date"],
                        event_count=0,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        total_cost_usd=0.0,
                    )
                    session.add(daily)

                daily.event_count += 1
                daily.prompt_tokens += int(event["prompt_tokens"])
                daily.completion_tokens += int(event["completion_tokens"])
                daily.total_tokens += int(event["total_tokens"])
                daily.total_cost_usd += float(event["cost_usd"])
                daily.updated_at = datetime.utcnow()
        except Exception as exc:  # noqa: BLE001
            _log.error("usage_event_db_save_failed", error=str(exc), user_id=event.get("user_id"))

    async def _get_daily_usage_from_db(self, user_id: str, usage_date: date) -> Dict[str, Any]:
        try:
            from sqlalchemy import select

            from .database import get_db_context
            from .models import UsageDailyAggregateModel

            async with get_db_context() as session:
                result = await session.execute(
                    select(UsageDailyAggregateModel).where(
                        UsageDailyAggregateModel.user_id == user_id,
                        UsageDailyAggregateModel.usage_date == usage_date,
                    )
                )
                daily = result.scalar_one_or_none()
                if daily is None:
                    return self._empty_daily_usage(user_id, usage_date)
                return {
                    "user_id": user_id,
                    "usage_date": usage_date.isoformat(),
                    "event_count": int(daily.event_count),
                    "prompt_tokens": int(daily.prompt_tokens),
                    "completion_tokens": int(daily.completion_tokens),
                    "total_tokens": int(daily.total_tokens),
                    "total_cost_usd": float(daily.total_cost_usd),
                    "updated_at": daily.updated_at.isoformat() if daily.updated_at else None,
                }
        except Exception as exc:  # noqa: BLE001
            _log.error(
                "usage_daily_db_read_failed",
                error=str(exc),
                user_id=user_id,
                usage_date=usage_date.isoformat(),
            )
            return self._empty_daily_usage(user_id, usage_date)

    @staticmethod
    def _empty_daily_usage(user_id: str, usage_date: date) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "usage_date": usage_date.isoformat(),
            "event_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "updated_at": None,
        }


usage_event_store = UsageEventStore()


async def get_usage_event_store() -> UsageEventStore:
    return usage_event_store


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.utcnow()


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
