from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.services.embedding_service import EmbeddingProviderUnavailableError
from api.services.memory_entries_service import MemoryEntriesService, chunk_text
from api.storage.vector_models import MemoryEntryModel


class _ScalarResult:
    def __init__(self, existing):
        self._existing = existing

    def scalar_one_or_none(self):
        return self._existing


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeSession:
    def __init__(self):
        self.existing = None
        self.rows: list[SimpleNamespace] = []
        self.added: list[object] = []

    async def execute(self, stmt, params=None):
        query_text = str(stmt)
        if "memory_entries" in query_text and "chunk_text ILIKE" in query_text:
            query = str((params or {}).get("query", "")).strip("%").lower()
            source_kinds = set((params or {}).get("source_kinds") or [])
            matched = [
                row
                for row in self.rows
                if query in str(row.chunk_text).lower()
                and (not source_kinds or row.source_kind in source_kinds)
            ]
            return _RowsResult(matched)
        if "memory_entries" in query_text:
            return _ScalarResult(self.existing)
        return _ScalarResult(None)

    def add(self, entry):
        self.added.append(entry)
        self.existing = entry
        self.rows.append(
            SimpleNamespace(
                id=entry.id,
                user_id=entry.user_id,
                source_kind=entry.source_kind,
                source_id=entry.source_id,
                chunk_index=entry.chunk_index,
                chunk_text=entry.chunk_text,
                repository=entry.repository,
                commit_sha=entry.commit_sha,
                run_id=entry.run_id,
                session_id=entry.session_id,
                conversation_id=entry.conversation_id,
                metadata=entry.metadata_,
                created_at=entry.created_at,
                score=1.0,
            )
        )

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_index_text_deduplicates_identical_content(monkeypatch):
    fake_session = _FakeSession()

    @asynccontextmanager
    async def _db_context():
        yield fake_session

    monkeypatch.setattr("api.services.memory_entries_service.get_db_context", _db_context)

    service = MemoryEntriesService()
    service.embedding_service.embed_batch = AsyncMock(return_value=[[0.1] * 1536])

    first_ids = await service.index_text(
        user_id="user-1",
        source_kind="repo_doc",
        source_id="doc-1",
        content="phase three hardening notes",
        repository="acme/goblin-assistant",
        metadata={"kind": "doc"},
    )
    second_ids = await service.index_text(
        user_id="user-1",
        source_kind="repo_doc",
        source_id="doc-1",
        content="phase three hardening notes",
        repository="acme/goblin-assistant",
        metadata={"kind": "doc"},
    )

    assert first_ids == second_ids
    assert len(fake_session.added) == 1


def test_chunk_text_uses_overlapping_windows():
    chunks = chunk_text(
        "one two three four five six seven eight nine ten eleven",
        chunk_tokens=4,
        overlap_tokens=2,
    )

    assert chunks == [
        "one two three four",
        "three four five six",
        "five six seven eight",
        "seven eight nine ten",
        "nine ten eleven",
    ]


def test_memory_entry_model_defines_hnsw_index():
    index_names = {index.name for index in MemoryEntryModel.__table__.indexes}

    assert "idx_memory_entries_embedding_hnsw" in index_names
    hnsw_index = next(
        index
        for index in MemoryEntryModel.__table__.indexes
        if index.name == "idx_memory_entries_embedding_hnsw"
    )
    assert hnsw_index.dialect_options["postgresql"]["using"] == "hnsw"


@pytest.mark.asyncio
async def test_search_falls_back_to_sql_and_filters_by_source_kind(monkeypatch):
    fake_session = _FakeSession()
    fake_session.rows.extend(
        [
            SimpleNamespace(
                id="1",
                user_id="user-1",
                source_kind="repo_doc",
                source_id="doc-1",
                chunk_index=0,
                chunk_text="phase three hardening notes",
                repository="acme/goblin-assistant",
                commit_sha=None,
                run_id=None,
                session_id=None,
                conversation_id=None,
                metadata={},
                created_at=SimpleNamespace(isoformat=lambda: "2026-07-04T00:00:00+00:00"),
                score=0.9,
            ),
            SimpleNamespace(
                id="2",
                user_id="user-1",
                source_kind="agent_run",
                source_id="run-1",
                chunk_index=0,
                chunk_text="unrelated runtime trace",
                repository=None,
                commit_sha=None,
                run_id="run-1",
                session_id=None,
                conversation_id=None,
                metadata={},
                created_at=SimpleNamespace(isoformat=lambda: "2026-07-03T00:00:00+00:00"),
                score=0.3,
            ),
        ]
    )

    @asynccontextmanager
    async def _readonly_db_context():
        yield fake_session

    monkeypatch.setattr(
        "api.services.memory_entries_service.get_readonly_db_context",
        _readonly_db_context,
    )

    service = MemoryEntriesService()
    service.embedding_service.embed_text = AsyncMock(
        side_effect=EmbeddingProviderUnavailableError("embedding service disabled")
    )

    results = await service.search(
        "phase three",
        user_id="user-1",
        source_kinds=["repo_doc"],
        limit=5,
    )

    assert len(results) == 1
    assert results[0]["source_kind"] == "repo_doc"
    assert results[0]["content"] == "phase three hardening notes"
