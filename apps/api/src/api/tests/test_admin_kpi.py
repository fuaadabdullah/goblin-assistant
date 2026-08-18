from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.admin_routes import router as admin_router
from api.admin_routes import kpi
from api.ops.security import OpsSecurityConfig, ops_security
from api.storage.tasks import task_store


@pytest.fixture(autouse=True)
def _ops_dev_env(monkeypatch):
    monkeypatch.setattr(OpsSecurityConfig, "ENVIRONMENT", "development")
    monkeypatch.setattr(OpsSecurityConfig, "REQUIRE_AUTH", False)
    ops_security.rate_limit_cache.clear()
    task_store._in_memory_tasks.clear()
    yield
    task_store._in_memory_tasks.clear()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1")
    return TestClient(app)


def _task(
    task_id: str,
    *,
    user_id: str,
    task_type: str,
    created_at: datetime,
    status: str = "completed",
    payload: dict | None = None,
    result: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "task_id": task_id,
        "user_id": user_id,
        "status": status,
        "task_type": task_type,
        "payload": payload or {},
        "result": result,
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
        "metadata": metadata or {},
    }


@pytest.fixture
async def _kpi_db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        from api.storage.models import Base

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_kpi_helpers_track_fallback_ttft_and_cost_per_user_day(monkeypatch):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)

    await task_store.save_task(
        "chat-1",
        _task(
            "chat-1",
            user_id="user-1",
            task_type="chat.completion",
            created_at=now - timedelta(hours=6),
            result={
                "selected_provider": "openai",
                "model": "gpt-4o-mini",
                "cost_usd": 0.2,
                "usage": {"total_tokens": 100},
                "used_fallback": False,
                "ttft_ms": 120.0,
                "retrieval_latency_ms": 9.0,
            },
            metadata={"latency_ms": 350.0},
        ),
    )
    await task_store.save_task(
        "chat-2",
        _task(
            "chat-2",
            user_id="user-1",
            task_type="chat.completion",
            created_at=now - timedelta(hours=1),
            result={
                "selected_provider": "anthropic",
                "model": "claude-3-5-sonnet",
                "cost_usd": 0.4,
                "usage": {"total_tokens": 100},
                "used_fallback": True,
                "ttft_ms": 180.0,
            },
            metadata={"latency_ms": 420.0},
        ),
    )
    await task_store.save_task(
        "dogfood-1",
        _task(
            "dogfood-1",
            user_id="ops",
            task_type="dogfood.external_ai",
            created_at=now - timedelta(minutes=10),
            payload={
                "primary_assistant": "Goblin",
                "external_ai": "Claude",
                "reason": "Needed a faster answer",
                "context": "Deadline pressure",
            },
            result={
                "primary_assistant": "Goblin",
                "external_ai": "Claude",
                "reason": "Needed a faster answer",
                "context": "Deadline pressure",
            },
            metadata={"source": "dashboard"},
        ),
    )

    monkeypatch.setattr(
        "api.storage.usage_events.usage_event_store.get_model_rollup",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        kpi.tool_tracer,
        "get_tool_trace_stats",
        lambda time_window_hours: {"stats": {"avg_success_rate": 0.875}},
    )
    monkeypatch.setattr(
        kpi.retrieval_tracer,
        "get_retrieval_history",
        AsyncMock(return_value=[{"retrieval_time_ms": 12.5}, {"retrieval_time_ms": 17.5}]),
    )
    benchmark_rows = [
        {
            "prompt_id": "prompt-1",
            "strategy": "goblin",
            "success": True,
            "cost_usd": 0.08,
        },
        {
            "prompt_id": "prompt-1",
            "strategy": "strongest",
            "success": True,
            "cost_usd": 0.14,
        },
        {
            "prompt_id": "prompt-2",
            "strategy": "goblin",
            "success": True,
            "cost_usd": 0.1,
        },
        {
            "prompt_id": "prompt-2",
            "strategy": "strongest",
            "success": True,
            "cost_usd": 0.2,
        },
        {
            "prompt_id": "prompt-3",
            "strategy": "goblin",
            "success": False,
            "cost_usd": 0.05,
        },
        {
            "prompt_id": "prompt-3",
            "strategy": "strongest",
            "success": True,
            "cost_usd": 0.12,
        },
    ]
    monkeypatch.setattr(
        kpi,
        "_latest_jsonl",
        lambda directory: Path("fake-bench.jsonl")
        if directory == kpi._BENCH_RESULTS
        else None,
    )
    monkeypatch.setattr(kpi, "_read_jsonl", lambda path: benchmark_rows if path == Path("fake-bench.jsonl") else [])

    system = await kpi._system_metrics(since)
    economics = await kpi._economics_metrics(since, 7)

    assert system["request_count"] == 2
    assert system["fallback_pct"] == 50.0
    assert system["provider_failure_pct"] == 0.0
    assert system["tool_success_pct"] == 87.5
    assert system["retrieval_latency_ms"] == 15.0
    assert system["ttft_ms"] is not None
    assert system["dogfood"]["total_entries"] == 1
    assert system["dogfood"]["reason_counts"]["needed a faster answer"] == 1

    assert economics["total_requests"] == 2
    assert economics["total_cost_usd"] == 0.6
    assert economics["cost_per_request_usd"] == 0.3
    assert economics["cost_per_user_day_usd"] == 0.085714
    assert economics["tokens_per_request"] == 100
    assert economics["savings_from_routing_usd"] == pytest.approx(0.16)


@pytest.mark.asyncio
async def test_ai_metrics_include_tool_accuracy_and_provider_model_evals(monkeypatch):
    class _Dispatcher:
        def debug_info(self):
            return {
                "routing_table": [
                    {
                        "configured": True,
                        "can_route": True,
                        "circuit_breaker": {"state": "closed"},
                    }
                ]
            }

    provider_dispatcher = import_module("api.providers.dispatcher")
    monkeypatch.setattr(provider_dispatcher, "dispatcher", _Dispatcher())
    monkeypatch.setattr(
        kpi.tool_tracer,
        "get_tool_trace_stats",
        lambda time_window_hours: {"stats": {"avg_success_rate": 0.9}},
    )

    rows = [
        {
            "run_id": "run-1",
            "strategy": "goblin",
            "prompt_id": "p-1",
            "success": True,
            "selected_provider": "openai",
            "selected_model": "gpt-4o-mini",
            "quality_score": 0.8,
            "cost_usd": 0.1,
            "ttft_ms": 120.0,
            "used_fallback": False,
        },
        {
            "run_id": "run-1",
            "strategy": "cheapest",
            "prompt_id": "p-1",
            "success": True,
            "selected_provider": "cheap",
            "selected_model": "cheap-model",
            "quality_score": 0.55,
            "cost_usd": 0.01,
            "ttft_ms": 40.0,
            "used_fallback": False,
        },
        {
            "run_id": "run-1",
            "strategy": "goblin",
            "prompt_id": "p-2",
            "success": True,
            "selected_provider": "openai",
            "selected_model": "gpt-4o-mini",
            "quality_score": 0.9,
            "cost_usd": 0.2,
            "ttft_ms": 150.0,
            "used_fallback": True,
        },
    ]

    monkeypatch.setattr(
        kpi,
        "_latest_jsonl",
        lambda directory: Path("fake.jsonl")
        if directory == kpi._BENCH_RESULTS
        else None,
    )
    monkeypatch.setattr(kpi, "_read_jsonl", lambda path: rows)

    metrics = await kpi._ai_metrics(window_hours=24)

    assert metrics["tool_selection_accuracy"] == 90.0
    assert metrics["provider_model_evals"][0]["provider"] == "openai"
    assert metrics["provider_model_evals"][0]["avg_quality_score"] == 0.85
    assert metrics["provider_model_evals"][0]["fallback_rate"] == 0.5


@pytest.mark.asyncio
async def test_product_metrics_count_goblins_from_catalog(
    _kpi_db_engine, monkeypatch
):
    from api.storage.models import (
        ConversationModel,
        MessageModel,
        SupportTicketModel,
        UserModel,
    )
    from api.storage.vector_models import MemoryFactModel

    since = datetime(2026, 8, 10, 12, 0, 0)
    _AsyncSession = sessionmaker(
        _kpi_db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    @asynccontextmanager
    async def _db_context():
        session = _AsyncSession()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    api_router_module = import_module("api.api_router")
    monkeypatch.setattr("api.storage.database.get_db_context", _db_context)
    monkeypatch.setattr(
        api_router_module,
        "get_goblins",
        AsyncMock(
            return_value=[
                {"id": "docs-writer"},
                {"id": "code-writer"},
                {"id": "search-goblin"},
                {"id": "analyze-goblin"},
            ]
        ),
    )

    async with _db_context() as session:
        session.add_all(
            [
                UserModel(
                    id="user-1",
                    email="user1@example.com",
                    created_at=since - timedelta(days=2),
                    is_active=True,
                ),
                UserModel(
                    id="user-2",
                    email="user2@example.com",
                    created_at=since + timedelta(days=1),
                    is_active=True,
                ),
            ]
        )
        session.add_all(
            [
                ConversationModel(
                    conversation_id="conv-1",
                    user_id="user-1",
                    title="Before window",
                    created_at=since - timedelta(days=1),
                ),
                ConversationModel(
                    conversation_id="conv-2",
                    user_id="user-1",
                    title="Returning window",
                    created_at=since + timedelta(hours=1),
                ),
                ConversationModel(
                    conversation_id="conv-3",
                    user_id="user-2",
                    title="New user window",
                    created_at=since + timedelta(hours=2),
                ),
            ]
        )
        session.add_all(
            [
                MessageModel(
                    message_id="msg-1",
                    conversation_id="conv-1",
                    role="user",
                    content="Earlier chat",
                    timestamp=since - timedelta(days=1),
                    metadata_={"conversation_category": "reference"},
                ),
                MessageModel(
                    message_id="msg-2",
                    conversation_id="conv-2",
                    role="user",
                    content="Returning user",
                    timestamp=since + timedelta(hours=1),
                    metadata_={"attachments": True, "context_assembly_enabled": True},
                ),
                MessageModel(
                    message_id="msg-3",
                    conversation_id="conv-2",
                    role="assistant",
                    content="Assistant reply",
                    timestamp=since + timedelta(hours=1, minutes=1),
                    metadata_={},
                ),
                MessageModel(
                    message_id="msg-4",
                    conversation_id="conv-3",
                    role="user",
                    content="Brand new user",
                    timestamp=since + timedelta(hours=2),
                    metadata_={"conversation_category": "onboarding"},
                ),
            ]
        )
        session.add(
            MemoryFactModel(
                id="mf-1",
                user_id="user-1",
                fact_text="Likes concise answers",
                created_at=since - timedelta(hours=3),
                category="preference",
                metadata_={},
            )
        )
        session.add(
            SupportTicketModel(
                ticket_id="beta-1",
                user_id=None,
                email="ava@example.com",
                category="beta_signal",
                priority=None,
                status="received",
                subject="Pilot signal: which-model",
                message="Which model am I using?",
                attachment_url=None,
                triage={},
                metadata_={
                    "source": "beta_signal",
                    "page": "/chat",
                    "tag": "which-model",
                    "name": "Ava",
                    "email": "ava@example.com",
                },
                created_at=since + timedelta(hours=3),
            )
        )

    metrics = await kpi._product_metrics(since)

    assert metrics["total_users"] == 2
    assert metrics["new_users_in_window"] == 1
    assert metrics["returning_users_in_window"] == 1
    assert metrics["total_conversations"] == 3
    assert metrics["conversations_in_window"] == 2
    assert metrics["chats_per_user"] == 1.5
    assert metrics["total_messages"] == 4
    assert metrics["avg_session_turns"] == pytest.approx(1.3)
    assert metrics["total_memory_facts"] == 1
    assert metrics["goblins_created"] == 4
    assert metrics["feature_usage"]["counts"]["attachments_used"] == 1
    assert metrics["pilot_signals"]["total_signals"] == 1
    assert metrics["pilot_signals"]["unique_participants"] == 1
    assert metrics["pilot_signals"]["top_tags"][0]["tag"] == "which-model"


def test_dogfood_log_round_trip_via_admin_route():
    client = _client()

    post = client.post(
        "/api/v1/admin/kpi/dogfood",
        json={
            "primary_assistant": "Goblin",
            "external_ai": "Claude",
            "reason": "Needed a quicker answer",
            "context": "I was comparing providers",
        },
    )

    assert post.status_code == 200
    body = post.json()["data"]
    assert body["primary_assistant"] == "Goblin"
    assert body["external_ai"] == "Claude"
    assert body["reason"] == "Needed a quicker answer"

    get = client.get("/api/v1/admin/kpi/dogfood?limit=5")
    assert get.status_code == 200
    summary = get.json()["data"]
    assert summary["total_entries"] == 1
    assert summary["recent_entries"][0]["external_ai"] == "Claude"
    assert summary["reason_counts"]["needed a quicker answer"] == 1


def test_kpi_route_uses_gathered_snapshot(monkeypatch):
    client = _client()
    monkeypatch.setattr(
        kpi,
        "_gather",
        AsyncMock(
            return_value=(
                {"request_count": 1, "success_count": 1, "failure_count": 0},
                {"total_requests": 1, "total_cost_usd": 0.1},
                {"total_users": 1},
                {"providers": {"total": 1}},
            )
        ),
    )

    response = client.get("/api/v1/admin/kpi?days=7")

    assert response.status_code == 200
    body = response.json()
    assert body["window_days"] == 7
    assert body["system"]["request_count"] == 1
    assert body["economics"]["total_cost_usd"] == 0.1
