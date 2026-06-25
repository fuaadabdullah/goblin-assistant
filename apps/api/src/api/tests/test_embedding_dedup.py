"""Tests for EmbeddingService DB pre-check and content hash deduplication."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.embedding_service import EmbeddingService


@pytest.fixture(autouse=True)
def reset_class_state():
    """Reset class-level dedup state before each test."""
    EmbeddingService._content_hash_cache.clear()
    EmbeddingService._duplicate_prevented_count = 0
    yield
    EmbeddingService._content_hash_cache.clear()
    EmbeddingService._duplicate_prevented_count = 0


@pytest.fixture
def svc() -> EmbeddingService:
    s = EmbeddingService.__new__(EmbeddingService)
    s.provider_name = "mock"
    s.model = "mock-model"
    s.dimension = 4
    s.max_input_tokens = 8000
    s._degraded_mode = False
    s._degraded_reason = None
    s.client = MagicMock()
    return s


# ---------------------------------------------------------------------------
# DB pre-check in store_message_embedding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_skipped_when_source_id_exists(svc):
    """If DB already has an embedding for message_id, embed_text must not be called."""
    # Simulate DB returning an existing row
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = ("existing-id",)
    mock_session.execute = AsyncMock(return_value=mock_result)

    embed_called = []

    async def raise_if_called(*args, **kwargs):
        embed_called.append(True)
        raise AssertionError("embed_text should not have been called")

    svc.embed_text = raise_if_called

    import api.services.embedding_service as em

    original = em.get_db_context

    class _FakeCtx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            pass

    em.get_db_context = lambda: _FakeCtx()  # noqa: PLW0108
    try:
        result = await svc.store_message_embedding("u1", "c1", "msg1", "hello world")
        assert result is True
        assert not embed_called
    finally:
        em.get_db_context = original


# ---------------------------------------------------------------------------
# Content hash cache deduplication
# ---------------------------------------------------------------------------


def test_first_call_registers_hash(svc):
    is_dup = EmbeddingService._check_and_register_hash("unique content")
    assert is_dup is False
    assert len(EmbeddingService._content_hash_cache) == 1
    assert EmbeddingService._duplicate_prevented_count == 0


def test_second_call_same_content_is_duplicate(svc):
    EmbeddingService._check_and_register_hash("same content")
    is_dup = EmbeddingService._check_and_register_hash("same content")
    assert is_dup is True
    assert EmbeddingService._duplicate_prevented_count == 1


def test_different_content_not_duplicate(svc):
    EmbeddingService._check_and_register_hash("content A")
    is_dup = EmbeddingService._check_and_register_hash("content B")
    assert is_dup is False
    assert EmbeddingService._duplicate_prevented_count == 0


def test_hash_cache_bounded_at_max_size():
    original_max = EmbeddingService._HASH_CACHE_MAX
    EmbeddingService._HASH_CACHE_MAX = 5
    try:
        for i in range(6):
            EmbeddingService._check_and_register_hash(f"unique content {i}")
        assert len(EmbeddingService._content_hash_cache) == 5
    finally:
        EmbeddingService._HASH_CACHE_MAX = original_max


def test_hash_cache_evicts_oldest_on_overflow():
    original_max = EmbeddingService._HASH_CACHE_MAX
    EmbeddingService._HASH_CACHE_MAX = 3
    try:
        EmbeddingService._check_and_register_hash("first")
        EmbeddingService._check_and_register_hash("second")
        EmbeddingService._check_and_register_hash("third")
        EmbeddingService._check_and_register_hash("fourth")  # should evict "first"
        # "first" evicted — not a duplicate anymore
        is_dup = EmbeddingService._check_and_register_hash("first")
        assert is_dup is False
    finally:
        EmbeddingService._HASH_CACHE_MAX = original_max


# ---------------------------------------------------------------------------
# get_dedup_stats
# ---------------------------------------------------------------------------


def test_get_dedup_stats_initial(svc):
    stats = svc.get_dedup_stats()
    assert stats["duplicates_prevented"] == 0
    assert stats["hash_cache_size"] == 0


def test_get_dedup_stats_after_dedup(svc):
    EmbeddingService._check_and_register_hash("content X")
    EmbeddingService._check_and_register_hash("content X")  # duplicate
    stats = svc.get_dedup_stats()
    assert stats["duplicates_prevented"] == 1
    assert stats["hash_cache_size"] == 1
