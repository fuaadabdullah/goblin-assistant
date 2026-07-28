import importlib
import uuid

import pytest


@pytest.mark.asyncio
async def test_retrieve_by_index_calls_retrieve_by_source_type(monkeypatch):
    """RetrievalService.retrieve_by_index should call the lower-level
    retrieve_by_source_type and pass through the embedding and params.
    """

    fake_embedding = [0.1, 0.2, 0.3]
    fake_return = [{"id": "1", "source_type": "document", "content": "x"}]

    rs_module = importlib.import_module("api.services.retrieval_service._retrieval_service")

    class _FakeEmbeddingService:
        async def embed_text(self, _text: str):
            return fake_embedding

    monkeypatch.setattr(rs_module, "EmbeddingService", _FakeEmbeddingService)

    captured = {}

    async def _fake_retrieve_by_source_type(*_args, **kwargs):
        # Accept both positional and keyword args to mirror real signature
        qe = kwargs.get("query_embedding") or (_args[0] if _args else None)
        uid = kwargs.get("user_id") or (_args[1] if len(_args) > 1 else None)
        stype = kwargs.get("source_type") or (_args[2] if len(_args) > 2 else None)
        k = kwargs.get("k", 5)
        captured["query_embedding"] = qe
        captured["user_id"] = uid
        captured["source_type"] = stype
        captured["k"] = k
        return fake_return

    monkeypatch.setattr(rs_module, "retrieve_by_source_type", _fake_retrieve_by_source_type)

    svc = rs_module.RetrievalService()
    user = f"test-user-{uuid.uuid4().hex[:8]}"

    results = await svc.retrieve_by_index(index_name="document", query="foo", user_id=user, k=3)

    assert results == fake_return
    assert captured["user_id"] == user
    assert captured["source_type"] == "document"
    assert captured["query_embedding"] == fake_embedding


@pytest.mark.asyncio
async def test_retrieve_by_source_type_maps_rows(monkeypatch):
    """Test mapping of SQL rows to dicts in retrieve_by_source_type by
    stubbing the DB session execute result."""

    sql_mod = importlib.import_module("api.services.retrieval_service._sql_retrieval")

    class Row:
        def __init__(
            self,
            id_,
            content,
            source_type,
            source_id,
            metadata,
            created_at,
            score,
        ):
            self.id = id_
            self.content = content
            self.source_type = source_type
            self.source_id = source_id
            self.metadata = metadata
            self.created_at = created_at
            self.score = score

    fake_rows = [Row("r1", "hello", "doc", "s1", {"k": "v"}, "ts", 0.9)]

    class _FakeResult:
        def fetchall(self):
            return fake_rows

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, *_args, **_kwargs):
            return _FakeResult()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_db_context():
        yield _FakeSession()

    monkeypatch.setattr(sql_mod, "get_readonly_db_context", _fake_db_context)

    results = await sql_mod.retrieve_by_source_type(
        query_embedding=[0.1], user_id="u1", source_type="doc", k=5
    )

    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]
    assert item["id"] == "r1"
    assert item["content"] == "hello"
    assert item["source_type"] == "doc"
    assert item["source_id"] == "s1"
