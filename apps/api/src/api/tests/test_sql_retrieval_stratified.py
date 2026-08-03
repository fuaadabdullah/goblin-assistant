"""Tests for _sql_retrieval module — stratified SQL retrieval functions."""

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from api.services.retrieval_service._sql_retrieval import (
    FINANCE_BOOST_FACTOR,
    FINANCE_CATEGORIES,
    GENERIC_BOOST_FACTOR,
    SUMMARY_BOOST_FACTOR,
    retrieve_memory_facts_stratified,
    retrieve_messages_stratified,
    retrieve_summaries_stratified,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers for mocking DB context and rows
# ──────────────────────────────────────────────────────────────────────────────


class FakeRow:
    """Mock database row."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeResult:
    """Mock query result."""

    def __init__(self, rows=None):
        self.rows = rows or []

    def fetchall(self):
        return self.rows


class FakeSession:
    """Mock database session."""

    def __init__(self, result_rows=None):
        self.result_rows = result_rows or []

    async def execute(self, query, params):
        return FakeResult(self.result_rows)


# ──────────────────────────────────────────────────────────────────────────────
# retrieve_memory_facts_stratified Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieve_memory_facts_stratified_success():
    """retrieve_memory_facts_stratified returns canonicalized memory facts."""

    row = FakeRow(
        id="fact-1",
        content="Important fact",
        fact_embedding=[0.1, 0.2, 0.3],
        category="instrument",
        memory_type="memory",
        source_kind="user",
        source_id="src-1",
        salience_score=0.8,
        confidence=0.95,
        memory_state="verified",
        sensitivity_level="public",
        retention_days=365,
        expires_at=None,
        last_accessed_at=None,
        confirmation_count=1,
        is_archived=False,
        related_memory_ids=[],
        entity_refs=[],
        metadata=None,
        created_at="2026-07-24T00:00:00",
        score=0.9,
    )

    @asynccontextmanager
    async def mock_db_context():
        yield FakeSession(result_rows=[row])

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_memory_facts_stratified(
            query_embedding=[0.1, 0.2, 0.3],
            user_id="user-1",
            k=3,
        )

        assert len(results) == 1
        assert results[0]["id"] == "fact-1"
        assert results[0]["content"] == "Important fact"
        assert results[0]["metadata"]["finance_boosted"] is True
        assert results[0]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_retrieve_memory_facts_stratified_finance_boost():
    """retrieve_memory_facts_stratified applies finance boost to risk_signal category."""

    row = FakeRow(
        id="fact-1",
        content="Finance fact",
        fact_embedding=[0.1],
        category="risk_signal",
        memory_type="memory",
        source_kind="user",
        source_id="src-1",
        salience_score=0.5,
        confidence=0.8,
        memory_state="active",
        sensitivity_level="private",
        retention_days=30,
        expires_at=None,
        last_accessed_at=None,
        confirmation_count=0,
        is_archived=False,
        related_memory_ids=[],
        entity_refs=[],
        metadata=None,
        created_at="2026-07-24",
        score=0.9 * FINANCE_BOOST_FACTOR,
    )

    @asynccontextmanager
    async def mock_db_context():
        yield FakeSession(result_rows=[row])

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_memory_facts_stratified(
            query_embedding=[0.1],
            user_id="user-1",
        )

        assert len(results) == 1
        assert results[0]["metadata"]["finance_boosted"] is True


@pytest.mark.asyncio
async def test_retrieve_memory_facts_stratified_exception_returns_empty():
    """retrieve_memory_facts_stratified returns empty list on exception."""

    @asynccontextmanager
    async def mock_db_context():
        raise Exception("Database connection failed")
        yield  # pragma: no cover

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_memory_facts_stratified(
            query_embedding=[0.1],
            user_id="user-1",
        )

        assert results == []


# ──────────────────────────────────────────────────────────────────────────────
# retrieve_summaries_stratified Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieve_summaries_stratified_success():
    """retrieve_summaries_stratified returns canonicalized summaries."""

    row = FakeRow(
        id="summary-1",
        conversation_id="conv-1",
        content="Summary of conversation",
        created_at="2026-07-24T00:00:00",
        score=0.85 * SUMMARY_BOOST_FACTOR,
    )

    @asynccontextmanager
    async def mock_db_context():
        yield FakeSession(result_rows=[row])

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_summaries_stratified(
            query_embedding=[0.1, 0.2],
            user_id="user-1",
            conversation_id="conv-1",
            k=2,
        )

        assert len(results) == 1
        assert results[0]["id"] == "summary-1"
        assert results[0]["content"] == "Summary of conversation"
        assert results[0]["metadata"]["source"] == "working_memory"


@pytest.mark.asyncio
async def test_retrieve_summaries_stratified_no_conversation_filter():
    """retrieve_summaries_stratified omits conversation filter when not provided."""

    @asynccontextmanager
    async def mock_db_context():
        yield FakeSession(result_rows=[])

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_summaries_stratified(
            query_embedding=[0.1],
            user_id="user-1",
            conversation_id=None,
        )

        assert results == []


@pytest.mark.asyncio
async def test_retrieve_summaries_stratified_exception_returns_empty():
    """retrieve_summaries_stratified returns empty list on exception."""

    @asynccontextmanager
    async def mock_db_context():
        raise Exception("Database error")
        yield  # pragma: no cover

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_summaries_stratified(
            query_embedding=[0.1],
            user_id="user-1",
        )

        assert results == []


# ──────────────────────────────────────────────────────────────────────────────
# retrieve_messages_stratified Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieve_messages_stratified_success():
    """retrieve_messages_stratified returns canonicalized messages."""

    row = FakeRow(
        id="msg-1",
        content="User message text",
        source_type="message",
        source_id="msg-1",
        conversation_id="conv-1",
        metadata={"role": "user"},
        created_at="2026-07-24T00:00:00",
        score=0.75,
    )

    @asynccontextmanager
    async def mock_db_context():
        yield FakeSession(result_rows=[row])

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_messages_stratified(
            query_embedding=[0.1, 0.2, 0.3],
            user_id="user-1",
            conversation_id="conv-1",
            k=3,
        )

        assert len(results) == 1
        assert results[0]["id"] == "msg-1"
        assert results[0]["content"] == "User message text"


@pytest.mark.asyncio
async def test_retrieve_messages_stratified_without_conversation():
    """retrieve_messages_stratified omits conversation filter when not provided."""

    @asynccontextmanager
    async def mock_db_context():
        yield FakeSession(result_rows=[])

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_messages_stratified(
            query_embedding=[0.1],
            user_id="user-1",
            conversation_id=None,
        )

        assert results == []


@pytest.mark.asyncio
async def test_retrieve_messages_stratified_exception_returns_empty():
    """retrieve_messages_stratified returns empty list on exception."""

    @asynccontextmanager
    async def mock_db_context():
        raise RuntimeError("Session error")
        yield  # pragma: no cover

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        return_value=mock_db_context(),
    ):
        results = await retrieve_messages_stratified(
            query_embedding=[0.1],
            user_id="user-1",
        )

        assert results == []


# ──────────────────────────────────────────────────────────────────────────────
# Constants Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_finance_categories_defined():
    """FINANCE_CATEGORIES contains expected categories."""
    assert "instrument" in FINANCE_CATEGORIES
    assert "risk_signal" in FINANCE_CATEGORIES
    assert "regulatory_constraint" in FINANCE_CATEGORIES
    assert "portfolio_action" in FINANCE_CATEGORIES
    assert "macro_event" in FINANCE_CATEGORIES


def test_boost_factors_reasonable():
    """Boost factors are in expected ranges and ordered properly."""
    assert FINANCE_BOOST_FACTOR > 1.0
    assert GENERIC_BOOST_FACTOR > 1.0
    assert SUMMARY_BOOST_FACTOR > 1.0
    assert FINANCE_BOOST_FACTOR > GENERIC_BOOST_FACTOR
    assert GENERIC_BOOST_FACTOR > SUMMARY_BOOST_FACTOR
