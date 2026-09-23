"""Tests for api.services.memory_core.repository — the DB layer behind
long-term memory: deprecating superseded facts, building a MemoryRecord from
an ORM row, and the upsert that creates or merges one.

The SQLAlchemy session is always a MagicMock/AsyncMock double built to hand
back whatever `execute().scalar_one_or_none()` the test wants; no test talks
to a real database. `_record_from_model` takes a plain row object (a
SimpleNamespace shaped like MemoryFactModel), since it only reads attributes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.memory_core import repository as repo
from api.services.memory_core.models import (
    MemoryKind,
    MemoryLifecycleState,
    MemorySensitivity,
)


def _row(**overrides: Any) -> SimpleNamespace:
    defaults: Dict[str, Any] = dict(
        id="mem-1",
        user_id="u-1",
        fact_text="likes dark mode",
        fact_embedding=None,
        category="preferences",
        memory_type="preference",
        source_kind="chat",
        source_id="msg-1",
        salience_score=0.6,
        confidence=0.7,
        memory_state="active",
        sensitivity_level="low",
        retention_days=30,
        expires_at=None,
        last_accessed_at=None,
        confirmation_count=1,
        is_archived=False,
        related_memory_ids=[],
        entity_refs=[],
        metadata_={},
        scope="global",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 1, 2, 12, 0, 0),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _session_returning(row: Any) -> MagicMock:
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=row)
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# _deprecate_conflicting_records
# ---------------------------------------------------------------------------


class TestDeprecateConflictingRecords:
    @pytest.mark.asyncio
    async def test_marks_a_matching_record_deprecated(self):
        row = _row(memory_state="active", is_archived=True)
        session = _session_returning(row)

        updated = await repo._deprecate_conflicting_records(
            session,
            user_id="u-1",
            memory_ids=["mem-1"],
            reason="superseded",
            replacement_memory_id="mem-2",
            metadata={"k": "v"},
        )

        assert updated == 1
        assert row.memory_state == MemoryLifecycleState.DEPRECATED.value
        assert row.is_archived is False
        assert row.metadata_["deprecated_reason"] == "superseded"
        assert row.metadata_["replacement_memory_id"] == "mem-2"

    @pytest.mark.asyncio
    async def test_missing_rows_are_skipped(self):
        session = _session_returning(None)

        updated = await repo._deprecate_conflicting_records(
            session,
            user_id="u-1",
            memory_ids=["missing"],
            reason="x",
            replacement_memory_id=None,
            metadata={},
        )

        assert updated == 0

    @pytest.mark.asyncio
    async def test_empty_ids_are_skipped_without_a_query(self):
        session = _session_returning(None)

        updated = await repo._deprecate_conflicting_records(
            session,
            user_id="u-1",
            memory_ids=["", None],
            reason="x",
            replacement_memory_id=None,
            metadata={},
        )

        assert updated == 0
        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_counts_every_matched_record(self):
        rows = [_row(id="a"), _row(id="b")]
        session = MagicMock()
        results = [MagicMock(scalar_one_or_none=MagicMock(return_value=r)) for r in rows]
        session.execute = AsyncMock(side_effect=results)

        updated = await repo._deprecate_conflicting_records(
            session,
            user_id="u-1",
            memory_ids=["a", "b"],
            reason="x",
            replacement_memory_id=None,
            metadata={},
        )

        assert updated == 2

    @pytest.mark.asyncio
    async def test_preserves_existing_metadata_keys(self):
        row = _row(metadata_={"existing": "keep-me"})
        session = _session_returning(row)

        await repo._deprecate_conflicting_records(
            session,
            user_id="u-1",
            memory_ids=["mem-1"],
            reason="x",
            replacement_memory_id=None,
            metadata={},
        )

        assert row.metadata_["existing"] == "keep-me"


# ---------------------------------------------------------------------------
# _record_from_model
# ---------------------------------------------------------------------------


class TestRecordFromModel:
    def test_builds_a_record_from_a_typical_row(self):
        row = _row()

        record = repo._record_from_model(row)

        assert record.id == "mem-1"
        assert record.content == "likes dark mode"
        assert record.confidence == 0.7
        assert record.scope == "global"
        assert record.confirmation_count == 1

    def test_naive_timestamps_are_assumed_utc(self):
        row = _row(created_at=datetime(2026, 1, 1))  # no tzinfo

        record = repo._record_from_model(row)

        assert record.created_at.tzinfo is not None

    def test_aware_timestamps_are_left_alone(self):
        aware = datetime(2026, 1, 1, tzinfo=timezone.utc)
        row = _row(created_at=aware)

        record = repo._record_from_model(row)

        assert record.created_at == aware

    def test_scope_falls_back_to_metadata_then_derivation(self):
        row = _row(scope=None, metadata_={}, source_kind="tool")

        record = repo._record_from_model(row)

        assert record.scope == "tool"

    def test_memory_state_derives_from_is_archived_when_unset(self):
        row = _row(memory_state=None, metadata_={}, is_archived=True)

        record = repo._record_from_model(row)

        assert record.is_archived is True

    def test_importance_prefers_explicit_metadata_over_salience(self):
        row = _row(salience_score=0.2, metadata_={"importance": 0.9})

        record = repo._record_from_model(row)

        assert record.importance == 0.9

    def test_importance_falls_back_to_salience_score(self):
        row = _row(salience_score=0.4, metadata_={})

        record = repo._record_from_model(row)

        assert record.importance == 0.4

    def test_confirmation_count_falls_back_to_repetition_metadata(self):
        row = _row(confirmation_count=0, metadata_={"repetition_count": 3})

        record = repo._record_from_model(row)

        assert record.repetition_count == 3

    def test_archived_and_deleted_states_mark_is_archived(self):
        deleted_row = _row(memory_state="deleted", is_archived=False)

        record = repo._record_from_model(deleted_row)

        assert record.is_archived is True

    def test_boolean_flags_are_read_from_metadata(self):
        row = _row(
            metadata_={
                "authored": True,
                "inferred": False,
                "direct_correction": True,
                "contradiction": False,
                "later_contradicted": True,
            }
        )

        record = repo._record_from_model(row)

        assert record.authored is True
        assert record.direct_correction is True
        assert record.later_contradicted is True

    def test_missing_updated_at_falls_back_to_created_at(self):
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        row = _row(created_at=created, updated_at=None)

        record = repo._record_from_model(row)

        assert record.updated_at == created

    def test_related_and_entity_refs_default_to_empty_lists(self):
        row = _row(related_memory_ids=None, entity_refs=None)

        record = repo._record_from_model(row)

        assert record.related_memory_ids == []
        assert record.entity_refs == []


# ---------------------------------------------------------------------------
# _upsert_memory_record
# ---------------------------------------------------------------------------


def _upsert_kwargs(**overrides: Any) -> Dict[str, Any]:
    defaults: Dict[str, Any] = dict(
        user_id="u-1",
        text="likes dark mode",
        source_kind="chat",
        source_id="msg-1",
        memory_type=MemoryKind.PREFERENCE,
        category="preferences",
        confidence=0.7,
        confidence_band="high",
        confidence_reason="explicit statement",
        importance=0.6,
        importance_band="medium",
        importance_reason="user preference",
        salience_score=0.6,
        sensitivity=MemorySensitivity.LOW,
        memory_state=MemoryLifecycleState.ACTIVE,
        retention_days=30,
        metadata={},
        related_memory_ids=[],
        entity_refs=[],
        scope="global",
        authored=True,
        inferred=False,
        direct_correction=False,
        contradiction=False,
        later_contradicted=False,
        repetition_count=1,
        explicitness_score=0.8,
    )
    defaults.update(overrides)
    return defaults


@pytest.fixture(autouse=True)
def _patch_entity_graph():
    with patch.object(repo, "_persist_entity_graph", AsyncMock()) as mock:
        yield mock


@pytest.fixture
def embedding_service() -> MagicMock:
    service = MagicMock()
    service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return service


class TestUpsertMemoryRecordCreate:
    @pytest.mark.asyncio
    async def test_creates_a_new_record_when_none_matches(self, embedding_service):
        session = _session_returning(None)  # no existing row

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            result = await repo._upsert_memory_record(embedding_service, **_upsert_kwargs())

        # Once for the memory fact, once for its embedding row.
        assert session.add.call_count == 2
        session.commit.assert_awaited_once()
        assert result is not None
        assert result.content == "likes dark mode"

    @pytest.mark.asyncio
    async def test_stores_an_embedding_row_when_embedding_succeeds(self, embedding_service):
        session = _session_returning(None)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            await repo._upsert_memory_record(embedding_service, **_upsert_kwargs())

        # One add() for the memory fact, one for the embedding row.
        assert session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_the_embedding_row_when_the_provider_is_unavailable(
        self, embedding_service
    ):
        from api.services.embedding_service import EmbeddingProviderUnavailableError

        embedding_service.embed_text = AsyncMock(
            side_effect=EmbeddingProviderUnavailableError("no key")
        )
        session = _session_returning(None)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            await repo._upsert_memory_record(embedding_service, **_upsert_kwargs())

        # Only the memory fact is added; no embedding row.
        assert session.add.call_count == 1

    @pytest.mark.asyncio
    async def test_an_unexpected_embedding_error_is_tolerated(self, embedding_service):
        embedding_service.embed_text = AsyncMock(side_effect=RuntimeError("provider down"))
        session = _session_returning(None)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            result = await repo._upsert_memory_record(embedding_service, **_upsert_kwargs())

        assert result is not None
        assert session.add.call_count == 1

    @pytest.mark.asyncio
    async def test_deprecates_conflicting_ids_before_creating(self, embedding_service):
        session = _session_returning(None)

        with (
            patch.object(repo, "get_db_context", return_value=_ctx(session)),
            patch.object(
                repo, "_deprecate_conflicting_records", AsyncMock(return_value=1)
            ) as deprecate,
        ):
            await repo._upsert_memory_record(
                embedding_service,
                **_upsert_kwargs(metadata={"supersedes_memory_ids": ["old-1"]}),
            )

        deprecate.assert_awaited_once()
        assert deprecate.await_args.kwargs["memory_ids"] == ["old-1"]

    @pytest.mark.asyncio
    async def test_entity_graph_failure_does_not_abort_the_upsert(
        self, embedding_service, _patch_entity_graph
    ):
        _patch_entity_graph.side_effect = RuntimeError("graph db down")
        session = _session_returning(None)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            result = await repo._upsert_memory_record(embedding_service, **_upsert_kwargs())

        assert result is not None
        session.commit.assert_awaited_once()


class TestUpsertMemoryRecordMerge:
    @pytest.mark.asyncio
    async def test_merges_into_an_existing_record(self, embedding_service):
        existing = _row(confirmation_count=2)
        session = _session_returning(existing)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            result = await repo._upsert_memory_record(
                embedding_service, **_upsert_kwargs(repetition_count=1)
            )

        assert existing.confirmation_count == 3
        session.add.assert_not_called()
        session.commit.assert_not_awaited()  # merge path flushes, doesn't commit
        session.flush.assert_awaited_once()
        assert result.id == existing.id

    @pytest.mark.asyncio
    async def test_confirmation_count_respects_a_larger_repetition_count(self, embedding_service):
        existing = _row(confirmation_count=1)
        session = _session_returning(existing)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            await repo._upsert_memory_record(
                embedding_service, **_upsert_kwargs(repetition_count=5)
            )

        assert existing.confirmation_count == 6

    @pytest.mark.asyncio
    async def test_merged_state_never_downgrades_from_archived(self, embedding_service):
        existing = _row(memory_state=MemoryLifecycleState.ARCHIVED.value)
        session = _session_returning(existing)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            await repo._upsert_memory_record(
                embedding_service,
                **_upsert_kwargs(memory_state=MemoryLifecycleState.ACTIVE),
            )

        assert existing.memory_state == MemoryLifecycleState.ARCHIVED.value
        assert existing.is_archived is True

    @pytest.mark.asyncio
    async def test_merge_preserves_the_stored_embedding_id(self, embedding_service):
        existing = _row(metadata_={"embedding_id": "emb-1"})
        session = _session_returning(existing)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            await repo._upsert_memory_record(embedding_service, **_upsert_kwargs())

        assert existing.metadata_["embedding_id"] == "emb-1"

    @pytest.mark.asyncio
    async def test_a_successful_embedding_replaces_the_stored_vector(self, embedding_service):
        existing = _row(fact_embedding=None)
        session = _session_returning(existing)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            await repo._upsert_memory_record(embedding_service, **_upsert_kwargs())

        assert existing.fact_embedding == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_merge_entity_graph_failure_does_not_abort(
        self, embedding_service, _patch_entity_graph
    ):
        _patch_entity_graph.side_effect = RuntimeError("graph db down")
        existing = _row()
        session = _session_returning(existing)

        with patch.object(repo, "get_db_context", return_value=_ctx(session)):
            result = await repo._upsert_memory_record(embedding_service, **_upsert_kwargs())

        assert result is not None
        session.refresh.assert_awaited_once()


def _ctx(session):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm()
