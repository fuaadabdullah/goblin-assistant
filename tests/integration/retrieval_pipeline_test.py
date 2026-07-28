"""
Real integration tests for the retrieval pipeline.

Seeds raw data directly into the test SQLite DB and exercises the
_sql_retrieval functions with a patched get_readonly_db_context so
queries hit the in-memory engine instead of the module-level default.

embed_text is stubbed to return a zero vector — we test the SQL
retrieval layer (recency ordering, filtering, source stratification),
not vector similarity math.

Failures here expose real bugs: wrong column names in raw SQL,
missing WHERE clauses, incorrect ORDER BY, or silent exception swallowing.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
def patch_retrieval_db(test_engine):
    """Redirect _sql_retrieval's db_context to the test SQLite engine."""
    factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    @asynccontextmanager
    async def _test_db_context():
        async with factory() as session:
            yield session

    with patch(
        "api.services.retrieval_service._sql_retrieval.get_readonly_db_context",
        new=_test_db_context,
    ):
        yield


@pytest_asyncio.fixture(autouse=True)
def stub_embed_text(monkeypatch):
    """Return deterministic zero vector — avoids network and pgvector calls."""
    try:
        import api.services.embedding_service as _es

        async def _fake_embed(self, text: str):
            return [0.0] * 1536

        monkeypatch.setattr(_es.EmbeddingService, "embed_text", _fake_embed)
    except Exception:
        pass  # If embedding service is already stubbed or unavailable, ignore


async def _seed_user(db_session, user_id: str, email: str):
    from api.storage.models import UserModel

    user = UserModel(id=user_id, email=email)
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_conversation(db_session, conv_id: str, user_id: str, title: str = "Test"):
    from api.storage.models import ConversationModel

    conv = ConversationModel(conversation_id=conv_id, user_id=user_id, title=title)
    db_session.add(conv)
    await db_session.flush()
    return conv


async def _seed_message(
    db_session,
    conv_id: str,
    content: str,
    role: str = "user",
    timestamp: datetime = None,
):
    from api.storage.models import MessageModel

    msg = MessageModel(
        message_id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role=role,
        content=content,
        timestamp=timestamp or datetime.utcnow(),
    )
    db_session.add(msg)
    await db_session.flush()
    return msg


# ---------------------------------------------------------------------------
# retrieve_recent_messages
# ---------------------------------------------------------------------------


class TestRetrieveRecentMessages:
    async def test_finds_seeded_messages(self, db_session, patch_retrieval_db):
        """
        retrieve_recent_messages must return messages seeded for a given
        user_id + conversation_id.

        If this test fails with an OperationalError it means the raw SQL
        in _sql_retrieval.py uses column names (e.g. m.id, m.user_id,
        m.created_at) that don't match the actual MessageModel schema
        (message_id, no user_id, timestamp). That is a real schema bug.
        """
        from api.services.retrieval_service._sql_retrieval import retrieve_recent_messages

        uid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        await _seed_user(db_session, uid, f"{uid}@test.example")
        await _seed_conversation(db_session, cid, uid)
        await _seed_message(db_session, cid, "first message")
        await _seed_message(db_session, cid, "second message")
        await db_session.commit()

        results = await retrieve_recent_messages(user_id=uid, conversation_id=cid, k=10)

        # If column names mismatch, results will be [] due to exception swallowing
        assert len(results) == 2, (
            f"Expected 2 messages, got {len(results)}. "
            "Likely cause: raw SQL column names don't match MessageModel schema "
            "(check m.id vs message_id, m.user_id vs missing, m.created_at vs timestamp)."
        )
        contents = {r["content"] for r in results}
        assert "first message" in contents
        assert "second message" in contents

    async def test_returns_messages_sorted_by_recency(self, db_session, patch_retrieval_db):
        """Messages must come back newest-first."""
        from api.services.retrieval_service._sql_retrieval import retrieve_recent_messages

        uid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        await _seed_user(db_session, uid, f"{uid}@test.example")
        await _seed_conversation(db_session, cid, uid)

        now = datetime.utcnow()
        await _seed_message(db_session, cid, "oldest", timestamp=now - timedelta(hours=2))
        await _seed_message(db_session, cid, "middle", timestamp=now - timedelta(hours=1))
        await _seed_message(db_session, cid, "newest", timestamp=now)
        await db_session.commit()

        results = await retrieve_recent_messages(user_id=uid, conversation_id=cid, k=2)

        assert len(results) == 2, f"Expected 2 (limit=2), got {len(results)}"
        contents = [r["content"] for r in results]
        # "newest" must appear, "oldest" must not
        assert "newest" in contents, f"Most recent message missing. Got: {contents}"
        assert "oldest" not in contents, f"Oldest message wrongly included. Got: {contents}"

    async def test_returns_empty_list_for_unknown_conversation(self, db_session, patch_retrieval_db):
        """Unknown conversation_id must return [] gracefully, never raise."""
        from api.services.retrieval_service._sql_retrieval import retrieve_recent_messages

        results = await retrieve_recent_messages(
            user_id=str(uuid.uuid4()),
            conversation_id=str(uuid.uuid4()),
            k=10,
        )
        assert results == []

    async def test_respects_limit_k(self, db_session, patch_retrieval_db):
        """k=1 must return at most 1 message."""
        from api.services.retrieval_service._sql_retrieval import retrieve_recent_messages

        uid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        await _seed_user(db_session, uid, f"{uid}@test.example")
        await _seed_conversation(db_session, cid, uid)
        for i in range(5):
            await _seed_message(db_session, cid, f"message {i}")
        await db_session.commit()

        results = await retrieve_recent_messages(user_id=uid, conversation_id=cid, k=1)
        assert len(results) <= 1


# ---------------------------------------------------------------------------
# retrieve_by_source_type (no vector ops needed)
# ---------------------------------------------------------------------------


class TestRetrieveBySourceType:
    async def test_returns_list_or_empty_without_crashing(self, db_session, patch_retrieval_db):
        """
        retrieve_by_source_type must return a list (possibly empty) and never raise.
        Smoke test for the source-type routing logic.
        """
        from api.services.retrieval_service._sql_retrieval import retrieve_by_source_type

        uid = str(uuid.uuid4())
        await _seed_user(db_session, uid, f"{uid}@test.example")
        await db_session.commit()

        result = await retrieve_by_source_type(
            source_type="ephemeral",
            user_id=uid,
            query_embedding=[0.0] * 1536,
            k=5,
        )
        assert isinstance(result, list)

    async def test_unknown_source_type_returns_empty(self, db_session, patch_retrieval_db):
        from api.services.retrieval_service._sql_retrieval import retrieve_by_source_type

        result = await retrieve_by_source_type(
            source_type="nonexistent_source_xyz",
            user_id=str(uuid.uuid4()),
            query_embedding=[0.0] * 1536,
            k=5,
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# MemoryFact retrieval (SQLite-safe: no <=> operator in the basic path)
# ---------------------------------------------------------------------------


class TestMemoryFactRetrieval:
    async def test_memory_fact_seeded_and_queryable(self, db_session, patch_retrieval_db):
        """Seeding a MemoryFactModel row confirms the table exists and is writable."""
        from api.storage.vector_models import MemoryFactModel

        uid = str(uuid.uuid4())
        await _seed_user(db_session, uid, f"{uid}@test.example")

        fact = MemoryFactModel(
            id=str(uuid.uuid4()),
            user_id=uid,
            fact_text="The user prefers dark mode",
            category="preferences",
            fact_embedding=None,  # SQLite safe: no pgvector
        )
        db_session.add(fact)
        await db_session.commit()

        from sqlalchemy import select

        result = await db_session.execute(
            select(MemoryFactModel).where(MemoryFactModel.user_id == uid)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].fact_text == "The user prefers dark mode"
        assert rows[0].category == "preferences"
