"""Tests for BackgroundTaskManager and ConversationSummarizationService.

The retry *predicate* is covered separately in test_background_tasks_retry.py;
this module covers the task lifecycle, the periodic loops, message analysis,
summary generation, and the on-demand summarization service.

Every periodic loop is `while self.running`, so each test drives exactly one
iteration and then clears the flag from inside a patched sleep — otherwise the
loop would spin forever.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services import background_tasks as bt
from api.services.background_tasks import (
    BackgroundTaskManager,
    ConversationSummarizationService,
    _SummaryGenerationError,
)


def _message(role: str = "user", content: str = "hi", classification: Optional[str] = None):
    metadata: Dict[str, Any] = {}
    if classification:
        metadata["classification"] = {"type": classification}
    return SimpleNamespace(role=role, content=content, metadata=metadata)


@asynccontextmanager
async def _ctx(session):
    yield session


def _stop_after_one_iteration(manager: BackgroundTaskManager):
    """Return a sleep stub that ends the loop after its first pass."""

    async def _sleep(_seconds):
        manager.running = False

    return _sleep


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_schedules_every_periodic_task(self):
        manager = BackgroundTaskManager()

        with patch.object(bt.asyncio, "create_task", side_effect=lambda coro: coro) as create_task:
            await manager.start()

        assert manager.running is True
        assert create_task.call_count == 4
        # Close the coroutines we intercepted so they don't warn about never
        # being awaited.
        for coro in manager.tasks:
            coro.close()
        manager.tasks.clear()

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with patch.object(bt.asyncio, "create_task") as create_task:
            await manager.start()

        create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_cancels_outstanding_tasks_and_clears_them(self):
        manager = BackgroundTaskManager()
        manager.running = True

        async def _forever():
            await asyncio.sleep(3600)

        task = asyncio.create_task(_forever())
        manager.tasks = [task]

        await manager.stop()

        assert manager.running is False
        assert manager.tasks == []
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_stop_is_a_noop_when_not_running(self):
        manager = BackgroundTaskManager()
        sentinel = MagicMock()
        manager.tasks = [sentinel]

        await manager.stop()

        sentinel.cancel.assert_not_called()
        assert manager.tasks == [sentinel]

    @pytest.mark.asyncio
    async def test_stop_leaves_already_finished_tasks_alone(self):
        manager = BackgroundTaskManager()
        manager.running = True

        async def _done():
            return None

        task = asyncio.create_task(_done())
        await task
        manager.tasks = [task]

        await manager.stop()

        assert manager.tasks == []


# ---------------------------------------------------------------------------
# Periodic loops
# ---------------------------------------------------------------------------


class TestPeriodicLoops:
    @pytest.mark.asyncio
    async def test_summarization_loop_runs_the_worker(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with (
            patch.object(manager, "_summarize_stale_conversations", AsyncMock()) as worker,
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_conversation_summarization()

        worker.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_summarization_loop_survives_worker_errors(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with (
            patch.object(
                manager, "_summarize_stale_conversations", AsyncMock(side_effect=RuntimeError("x"))
            ),
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_conversation_summarization()

        assert manager.running is False

    @pytest.mark.asyncio
    async def test_summarization_loop_exits_on_cancellation(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with patch.object(
            manager, "_summarize_stale_conversations", AsyncMock(side_effect=asyncio.CancelledError)
        ):
            await manager._periodic_conversation_summarization()

        # Breaking out rather than propagating is what lets stop() gather cleanly.
        assert manager.running is True

    @pytest.mark.asyncio
    async def test_embedding_cleanup_loop_runs_the_worker(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with (
            patch.object(manager, "_cleanup_old_embeddings", AsyncMock()) as worker,
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_embedding_cleanup()

        worker.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_embedding_cleanup_loop_exits_on_cancellation(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with patch.object(
            manager, "_cleanup_old_embeddings", AsyncMock(side_effect=asyncio.CancelledError)
        ):
            await manager._periodic_embedding_cleanup()

        assert manager.running is True

    @pytest.mark.asyncio
    async def test_embedding_cleanup_loop_survives_errors(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with (
            patch.object(
                manager, "_cleanup_old_embeddings", AsyncMock(side_effect=RuntimeError("x"))
            ),
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_embedding_cleanup()

        assert manager.running is False

    @pytest.mark.asyncio
    async def test_index_optimization_loop_runs_the_worker(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with (
            patch.object(manager, "_optimize_vector_indexes", AsyncMock()) as worker,
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_index_optimization()

        worker.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_index_optimization_loop_exits_on_cancellation(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with patch.object(
            manager, "_optimize_vector_indexes", AsyncMock(side_effect=asyncio.CancelledError)
        ):
            await manager._periodic_index_optimization()

        assert manager.running is True

    @pytest.mark.asyncio
    async def test_index_optimization_loop_survives_errors(self):
        manager = BackgroundTaskManager()
        manager.running = True

        with (
            patch.object(
                manager, "_optimize_vector_indexes", AsyncMock(side_effect=RuntimeError("x"))
            ),
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_index_optimization()

        assert manager.running is False


class TestPeriodicLearningApplication:
    @pytest.mark.asyncio
    async def test_applies_a_batch(self, monkeypatch):
        manager = BackgroundTaskManager()
        manager.running = True
        applicator = SimpleNamespace(apply_batch=AsyncMock(return_value=5))
        monkeypatch.setitem(
            __import__("sys").modules,
            "api.services.learning_applicator",
            SimpleNamespace(learning_applicator=applicator),
        )
        session = MagicMock()

        with (
            patch.object(bt, "get_db_context", lambda: _ctx(session)),
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_learning_application()

        applicator.apply_batch.assert_awaited_once_with(session, limit=200)

    @pytest.mark.asyncio
    async def test_tolerates_nothing_to_apply(self, monkeypatch):
        manager = BackgroundTaskManager()
        manager.running = True
        applicator = SimpleNamespace(apply_batch=AsyncMock(return_value=0))
        monkeypatch.setitem(
            __import__("sys").modules,
            "api.services.learning_applicator",
            SimpleNamespace(learning_applicator=applicator),
        )

        with (
            patch.object(bt, "get_db_context", lambda: _ctx(MagicMock())),
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_learning_application()

        applicator.apply_batch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_survives_applicator_errors(self, monkeypatch):
        manager = BackgroundTaskManager()
        manager.running = True
        applicator = SimpleNamespace(apply_batch=AsyncMock(side_effect=RuntimeError("db down")))
        monkeypatch.setitem(
            __import__("sys").modules,
            "api.services.learning_applicator",
            SimpleNamespace(learning_applicator=applicator),
        )

        with (
            patch.object(bt, "get_db_context", lambda: _ctx(MagicMock())),
            patch.object(bt.asyncio, "sleep", _stop_after_one_iteration(manager)),
        ):
            await manager._periodic_learning_application()

        assert manager.running is False


# ---------------------------------------------------------------------------
# _analyze_message_types
# ---------------------------------------------------------------------------


class TestAnalyzeMessageTypes:
    def test_defaults_unclassified_messages_to_chat(self):
        manager = BackgroundTaskManager()

        analysis = manager._analyze_message_types([_message(), _message()])

        assert analysis["type_distribution"] == {"chat": 2}
        assert analysis["key_facts"] == []

    def test_buckets_facts_preferences_and_tasks(self):
        manager = BackgroundTaskManager()
        messages = [
            _message(content="a fact", classification="fact"),
            _message(content="a preference", classification="preference"),
            _message(content="a task", classification="task_result"),
        ]

        analysis = manager._analyze_message_types(messages)

        assert analysis["key_facts"] == ["a fact"]
        assert analysis["key_preferences"] == ["a preference"]
        assert analysis["tasks"] == ["a task"]
        assert analysis["type_distribution"] == {"fact": 1, "preference": 1, "task_result": 1}

    def test_keeps_only_the_first_three_of_each_bucket(self):
        manager = BackgroundTaskManager()
        messages = [_message(content=f"fact {i}", classification="fact") for i in range(5)]

        analysis = manager._analyze_message_types(messages)

        assert analysis["key_facts"] == ["fact 0", "fact 1", "fact 2"]
        assert analysis["type_distribution"] == {"fact": 5}

    def test_truncates_long_content_to_100_characters(self):
        manager = BackgroundTaskManager()
        messages = [_message(content="x" * 250, classification="fact")]

        analysis = manager._analyze_message_types(messages)

        assert analysis["key_facts"] == ["x" * 100]

    def test_tolerates_messages_without_metadata(self):
        manager = BackgroundTaskManager()
        bare = SimpleNamespace(role="user", content="hi", metadata=None)

        analysis = manager._analyze_message_types([bare])

        assert analysis["type_distribution"] == {"chat": 1}


# ---------------------------------------------------------------------------
# _generate_summary_with_retry
# ---------------------------------------------------------------------------


class TestGenerateSummaryWithRetry:
    @pytest.mark.asyncio
    async def test_returns_the_trimmed_provider_text(self):
        manager = BackgroundTaskManager()
        response = {"ok": True, "result": {"text": "  a summary  "}}

        with patch.object(bt, "invoke_provider", AsyncMock(return_value=response)):
            assert await manager._generate_summary_with_retry("prompt") == "a summary"

    @pytest.mark.asyncio
    async def test_returns_none_when_the_provider_keeps_failing(self):
        manager = BackgroundTaskManager()
        response = {"ok": False, "error": "auth denied", "error_category": "auth"}

        with patch.object(bt, "invoke_provider", AsyncMock(return_value=response)) as invoke:
            result = await manager._generate_summary_with_retry("prompt", max_retries=3)

        assert result is None
        # "auth" is not retryable, so exactly one attempt is made.
        assert invoke.await_count == 1

    @pytest.mark.asyncio
    async def test_retries_transient_failures_then_succeeds(self):
        manager = BackgroundTaskManager()
        responses = [
            {"ok": False, "error": "busy", "error_category": "rate-limit"},
            {"ok": True, "result": {"text": "second try"}},
        ]

        with (
            patch.object(bt, "invoke_provider", AsyncMock(side_effect=responses)) as invoke,
            patch("tenacity.nap.time.sleep"),
            patch.object(asyncio, "sleep", AsyncMock()),
        ):
            result = await manager._generate_summary_with_retry("prompt", max_retries=3)

        assert result == "second try"
        assert invoke.await_count == 2

    @pytest.mark.asyncio
    async def test_empty_text_is_treated_as_a_server_error(self):
        manager = BackgroundTaskManager()
        response = {"ok": True, "result": {"text": "   "}}

        with (
            patch.object(bt, "invoke_provider", AsyncMock(return_value=response)) as invoke,
            patch("tenacity.nap.time.sleep"),
            patch.object(asyncio, "sleep", AsyncMock()),
        ):
            result = await manager._generate_summary_with_retry("prompt", max_retries=2)

        assert result is None
        # server-error is retryable, so it exhausts the attempt budget.
        assert invoke.await_count == 2

    @pytest.mark.asyncio
    async def test_non_dict_provider_response_is_an_error(self):
        manager = BackgroundTaskManager()

        with patch.object(bt, "invoke_provider", AsyncMock(return_value="weird")):
            assert await manager._generate_summary_with_retry("prompt") is None

    @pytest.mark.asyncio
    async def test_unexpected_exceptions_return_none(self):
        manager = BackgroundTaskManager()

        with patch.object(bt, "invoke_provider", AsyncMock(side_effect=ValueError("bad"))):
            assert await manager._generate_summary_with_retry("prompt") is None


# ---------------------------------------------------------------------------
# _summarize_conversation
# ---------------------------------------------------------------------------


class TestSummarizeConversation:
    @pytest.mark.asyncio
    async def test_returns_early_for_a_missing_conversation(self):
        manager = BackgroundTaskManager()

        with (
            patch.object(bt.conversation_store, "get_conversation", AsyncMock(return_value=None)),
            patch.object(manager, "_generate_summary_with_retry", AsyncMock()) as generate,
        ):
            await manager._summarize_conversation("c-1", "u-1")

        generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_early_for_a_conversation_without_messages(self):
        manager = BackgroundTaskManager()
        conversation = SimpleNamespace(messages=[], user_id="u-1")

        with (
            patch.object(
                bt.conversation_store, "get_conversation", AsyncMock(return_value=conversation)
            ),
            patch.object(manager, "_generate_summary_with_retry", AsyncMock()) as generate,
        ):
            await manager._summarize_conversation("c-1", "u-1")

        generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_stores_the_generated_summary(self):
        manager = BackgroundTaskManager()
        conversation = SimpleNamespace(messages=[_message(content="hello")], user_id="u-1")
        store = AsyncMock(return_value=True)

        with (
            patch.object(
                bt.conversation_store, "get_conversation", AsyncMock(return_value=conversation)
            ),
            patch.object(manager, "_generate_summary_with_retry", AsyncMock(return_value="sum")),
            patch.object(
                bt._retrieval_singleton.embedding_service, "store_conversation_summary", store
            ),
        ):
            await manager._summarize_conversation("c-1", "u-1")

        store.assert_awaited_once_with(conversation_id="c-1", summary_text="sum")

    @pytest.mark.asyncio
    async def test_logs_but_does_not_raise_when_storage_fails(self):
        manager = BackgroundTaskManager()
        conversation = SimpleNamespace(messages=[_message()], user_id="u-1")

        with (
            patch.object(
                bt.conversation_store, "get_conversation", AsyncMock(return_value=conversation)
            ),
            patch.object(manager, "_generate_summary_with_retry", AsyncMock(return_value="sum")),
            patch.object(
                bt._retrieval_singleton.embedding_service,
                "store_conversation_summary",
                AsyncMock(return_value=False),
            ),
        ):
            await manager._summarize_conversation("c-1", "u-1")

    @pytest.mark.asyncio
    async def test_skips_storage_when_no_summary_was_produced(self):
        manager = BackgroundTaskManager()
        conversation = SimpleNamespace(messages=[_message()], user_id="u-1")
        store = AsyncMock()

        with (
            patch.object(
                bt.conversation_store, "get_conversation", AsyncMock(return_value=conversation)
            ),
            patch.object(manager, "_generate_summary_with_retry", AsyncMock(return_value=None)),
            patch.object(
                bt._retrieval_singleton.embedding_service, "store_conversation_summary", store
            ),
        ):
            await manager._summarize_conversation("c-1", "u-1")

        store.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_swallows_unexpected_errors(self):
        manager = BackgroundTaskManager()

        with patch.object(
            bt.conversation_store, "get_conversation", AsyncMock(side_effect=RuntimeError("boom"))
        ):
            await manager._summarize_conversation("c-1", "u-1")

    @pytest.mark.asyncio
    async def test_only_the_most_recent_messages_are_summarized(self):
        manager = BackgroundTaskManager()
        messages = [_message(content=f"m{i}") for i in range(10)]
        conversation = SimpleNamespace(messages=messages, user_id="u-1")

        with (
            patch.object(
                bt.conversation_store, "get_conversation", AsyncMock(return_value=conversation)
            ),
            patch.object(
                manager, "_generate_summary_with_retry", AsyncMock(return_value="s")
            ) as generate,
            patch.object(
                bt._retrieval_singleton.embedding_service,
                "store_conversation_summary",
                AsyncMock(return_value=True),
            ),
        ):
            await manager._summarize_conversation("c-1", "u-1", max_messages=3)

        prompt = generate.await_args.args[0]
        assert "m9" in prompt
        assert "m6" not in prompt
        assert "Total messages: 3" in prompt


# ---------------------------------------------------------------------------
# _summarize_stale_conversations
# ---------------------------------------------------------------------------


class TestSummarizeStaleConversations:
    @pytest.mark.asyncio
    async def test_summarizes_each_returned_conversation(self):
        manager = BackgroundTaskManager()
        rows = [
            SimpleNamespace(conversation_id="c-1", user_id="u-1"),
            SimpleNamespace(conversation_id="c-2", user_id="u-2"),
        ]
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(fetchall=MagicMock(return_value=rows)))

        with (
            patch.object(bt, "get_readonly_db_context", lambda: _ctx(session)),
            patch.object(manager, "_summarize_conversation", AsyncMock()) as summarize,
        ):
            await manager._summarize_stale_conversations()

        assert summarize.await_count == 2
        assert summarize.await_args_list[0].args[0] == "c-1"

    @pytest.mark.asyncio
    async def test_one_failure_does_not_stop_the_batch(self):
        manager = BackgroundTaskManager()
        rows = [
            SimpleNamespace(conversation_id="c-1", user_id="u-1"),
            SimpleNamespace(conversation_id="c-2", user_id="u-2"),
        ]
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(fetchall=MagicMock(return_value=rows)))

        with (
            patch.object(bt, "get_readonly_db_context", lambda: _ctx(session)),
            patch.object(
                manager,
                "_summarize_conversation",
                AsyncMock(side_effect=[RuntimeError("bad"), None]),
            ) as summarize,
        ):
            await manager._summarize_stale_conversations()

        assert summarize.await_count == 2


# ---------------------------------------------------------------------------
# _cleanup_old_embeddings / _optimize_vector_indexes
# ---------------------------------------------------------------------------


class TestMaintenanceWorkers:
    @pytest.mark.asyncio
    async def test_cleanup_reports_stale_embeddings(self):
        manager = BackgroundTaskManager()
        session = MagicMock()
        session.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=SimpleNamespace(count=12)))
        )

        with patch.object(bt, "get_readonly_db_context", lambda: _ctx(session)):
            await manager._cleanup_old_embeddings()

        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cleanup_is_quiet_when_nothing_is_stale(self):
        manager = BackgroundTaskManager()
        session = MagicMock()
        session.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=SimpleNamespace(count=0)))
        )

        with patch.object(bt, "get_readonly_db_context", lambda: _ctx(session)):
            await manager._cleanup_old_embeddings()

    @pytest.mark.asyncio
    async def test_index_optimization_runs_every_statement_then_commits(self):
        manager = BackgroundTaskManager()
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with patch.object(bt, "get_db_context", lambda: _ctx(session)):
            await manager._optimize_vector_indexes()

        assert session.execute.await_count == 4
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_index_optimization_swallows_database_errors(self):
        manager = BackgroundTaskManager()
        session = MagicMock()
        session.execute = AsyncMock(side_effect=RuntimeError("no pgvector"))

        with patch.object(bt, "get_db_context", lambda: _ctx(session)):
            await manager._optimize_vector_indexes()


# ---------------------------------------------------------------------------
# ConversationSummarizationService
# ---------------------------------------------------------------------------


class TestConversationSummarizationService:
    @pytest.mark.asyncio
    async def test_refuses_when_a_recent_summary_exists(self):
        service = ConversationSummarizationService()
        session = MagicMock()
        session.execute = AsyncMock(
            return_value=MagicMock(fetchone=MagicMock(return_value=SimpleNamespace(updated_at=1)))
        )

        with patch.object(bt, "get_readonly_db_context", lambda: _ctx(session)):
            result = await service.summarize_conversation("c-1")

        assert result["success"] is False
        assert result["message"] == "Recent summary already exists"

    @pytest.mark.asyncio
    async def test_force_resummarize_skips_the_freshness_check(self):
        service = ConversationSummarizationService()
        conversation = SimpleNamespace(user_id="u-1")

        with (
            patch.object(bt, "get_readonly_db_context", MagicMock()) as readonly,
            patch.object(
                bt.conversation_store, "get_conversation", AsyncMock(return_value=conversation)
            ),
            patch.object(bt.background_task_manager, "_summarize_conversation", AsyncMock()),
        ):
            result = await service.summarize_conversation("c-1", force_resummarize=True)

        assert result["success"] is True
        readonly.assert_not_called()

    @pytest.mark.asyncio
    async def test_reports_a_missing_conversation(self):
        service = ConversationSummarizationService()
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=None)))

        with (
            patch.object(bt, "get_readonly_db_context", lambda: _ctx(session)),
            patch.object(bt.conversation_store, "get_conversation", AsyncMock(return_value=None)),
        ):
            result = await service.summarize_conversation("c-1")

        assert result["success"] is False
        assert result["message"] == "Conversation not found"

    @pytest.mark.asyncio
    async def test_reports_a_conversation_without_an_owner(self):
        service = ConversationSummarizationService()
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=None)))
        conversation = SimpleNamespace(user_id=None)

        with (
            patch.object(bt, "get_readonly_db_context", lambda: _ctx(session)),
            patch.object(
                bt.conversation_store, "get_conversation", AsyncMock(return_value=conversation)
            ),
        ):
            result = await service.summarize_conversation("c-1")

        assert result["success"] is False
        assert result["message"] == "Conversation has no user_id"

    @pytest.mark.asyncio
    async def test_delegates_to_the_task_manager_on_success(self):
        service = ConversationSummarizationService()
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=None)))
        conversation = SimpleNamespace(user_id="u-1")

        with (
            patch.object(bt, "get_readonly_db_context", lambda: _ctx(session)),
            patch.object(
                bt.conversation_store, "get_conversation", AsyncMock(return_value=conversation)
            ),
            patch.object(
                bt.background_task_manager, "_summarize_conversation", AsyncMock()
            ) as summarize,
        ):
            result = await service.summarize_conversation("c-1", max_messages=7)

        assert result["success"] is True
        assert "summarized_at" in result
        summarize.assert_awaited_once_with(conversation_id="c-1", user_id="u-1", max_messages=7)

    @pytest.mark.asyncio
    async def test_wraps_unexpected_errors_in_a_failure_payload(self):
        service = ConversationSummarizationService()

        with patch.object(
            bt, "get_readonly_db_context", MagicMock(side_effect=RuntimeError("db gone"))
        ):
            result = await service.summarize_conversation("c-1")

        assert result["success"] is False
        assert "db gone" in result["message"]
        assert result["conversation_id"] == "c-1"


def test_module_exposes_a_shared_manager_instance():
    assert isinstance(bt.background_task_manager, BackgroundTaskManager)


def test_summary_generation_error_is_an_exception():
    error = _SummaryGenerationError(None, "no category")
    assert isinstance(error, Exception)
    assert error.category is None
