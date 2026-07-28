"""
Tests for Conversation, ConversationMessage, and ConversationStoreManager.

Covers:
- ConversationMessage domain object (creation, to_dict, from_dict)
- Conversation domain object (creation, add_message, to_dict, from_dict)
- ConversationStoreManager (environment-aware selection, delegation, create_conversation,
  add_message_to_conversation, import_messages_to_conversation, check_conversation_owner)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from api.storage.conversations import (
    Conversation,
    ConversationMessage,
    ConversationStore,
    ConversationStoreManager,
    InMemoryConversationStore,
)

# ---------------------------------------------------------------------------
# ConversationMessage
# ---------------------------------------------------------------------------


class TestConversationMessage:
    def test_creates_with_defaults(self):
        msg = ConversationMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.message_id is not None
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}

    def test_creates_with_explicit_values(self):
        now = datetime.utcnow()
        msg = ConversationMessage(
            role="assistant",
            content="world",
            message_id="msg-123",
            timestamp=now,
            metadata={"source": "test"},
        )
        assert msg.message_id == "msg-123"
        assert msg.role == "assistant"
        assert msg.content == "world"
        assert msg.timestamp == now
        assert msg.metadata == {"source": "test"}

    def test_to_dict_roundtrip(self):
        now = datetime.utcnow()
        msg = ConversationMessage(
            role="user",
            content="roundtrip",
            message_id="rt-1",
            timestamp=now,
            metadata={"k": "v"},
        )
        d = msg.to_dict()
        assert d["message_id"] == "rt-1"
        assert d["role"] == "user"
        assert d["content"] == "roundtrip"
        assert d["timestamp"] == now.isoformat()
        assert d["metadata"] == {"k": "v"}

    def test_from_dict_restores(self):
        now = datetime.utcnow()
        d = {
            "message_id": "fd-1",
            "role": "assistant",
            "content": "from dict",
            "timestamp": now.isoformat(),
            "metadata": {"a": 1},
        }
        msg = ConversationMessage.from_dict(d)
        assert msg.message_id == "fd-1"
        assert msg.role == "assistant"
        assert msg.content == "from dict"
        assert msg.timestamp == now
        assert msg.metadata == {"a": 1}

    def test_from_dict_defaults_metadata(self):
        now = datetime.utcnow()
        d = {
            "message_id": "fd-2",
            "role": "user",
            "content": "no meta",
            "timestamp": now.isoformat(),
        }
        msg = ConversationMessage.from_dict(d)
        assert msg.metadata == {}


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


class TestConversation:
    def test_creates_with_defaults(self):
        conv = Conversation()
        assert conv.conversation_id is not None
        assert conv.title == "New Conversation"
        assert conv.messages == []
        assert conv.created_at is not None
        assert conv.updated_at is not None
        assert conv.last_accessed is not None
        assert conv.metadata == {}

    def test_creates_with_explicit_values(self):
        now = datetime.utcnow()
        msg = ConversationMessage(role="user", content="hi")
        conv = Conversation(
            conversation_id="conv-1",
            user_id="user-1",
            title="My Chat",
            messages=[msg],
            created_at=now,
            updated_at=now,
            metadata={"env": "test"},
        )
        assert conv.conversation_id == "conv-1"
        assert conv.user_id == "user-1"
        assert conv.title == "My Chat"
        assert len(conv.messages) == 1
        assert conv.messages[0].content == "hi"
        assert conv.created_at == now
        assert conv.updated_at == now
        assert conv.metadata == {"env": "test"}

    def test_add_message_sorts_and_updates_timestamp(self):
        base = datetime.utcnow()
        m1 = ConversationMessage(
            role="user",
            content="first",
            timestamp=base + timedelta(seconds=10),
        )
        m2 = ConversationMessage(
            role="assistant",
            content="second",
            timestamp=base + timedelta(seconds=20),
        )
        m3 = ConversationMessage(
            role="user",
            content="earlier",
            timestamp=base + timedelta(seconds=5),
        )
        conv = Conversation(messages=[m1, m2], updated_at=m2.timestamp)
        conv.add_message(m3)

        # messages should be sorted by timestamp
        timestamps = [m.timestamp for m in conv.messages]
        assert timestamps == sorted(timestamps)
        assert conv.messages[0].content == "earlier"
        assert conv.messages[1].content == "first"
        assert conv.messages[2].content == "second"

        # updated_at should still be the max (m2.timestamp), since m3 is earlier
        assert conv.updated_at == m2.timestamp

    def test_to_dict_roundtrip(self):
        now = datetime.utcnow()
        msg = ConversationMessage(
            role="user",
            content="hello",
            timestamp=now,
        )
        conv = Conversation(
            conversation_id="ctd-1",
            user_id="u-1",
            title="Roundtrip",
            messages=[msg],
            created_at=now,
            updated_at=now,
            metadata={"version": 1},
        )
        d = conv.to_dict()
        assert d["conversation_id"] == "ctd-1"
        assert d["user_id"] == "u-1"
        assert d["title"] == "Roundtrip"
        assert len(d["messages"]) == 1
        assert d["messages"][0]["content"] == "hello"
        assert d["created_at"] == now.isoformat()
        assert d["metadata"] == {"version": 1}

    def test_from_dict_restores(self):
        now = datetime.utcnow()
        d = {
            "conversation_id": "fd-1",
            "user_id": "u-1",
            "title": "From Dict",
            "messages": [
                {
                    "message_id": "m-1",
                    "role": "user",
                    "content": "hi",
                    "timestamp": now.isoformat(),
                    "metadata": {},
                }
            ],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "last_accessed": now.isoformat(),
            "metadata": {},
        }
        conv = Conversation.from_dict(d)
        assert conv.conversation_id == "fd-1"
        assert conv.user_id == "u-1"
        assert conv.title == "From Dict"
        assert len(conv.messages) == 1
        assert conv.messages[0].content == "hi"

    def test_from_dict_missing_last_accessed(self):
        now = datetime.utcnow()
        d = {
            "conversation_id": "fd-2",
            "user_id": "u-1",
            "title": "No Last Accessed",
            "messages": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": {},
        }
        conv = Conversation.from_dict(d)
        assert conv.last_accessed is not None

    def test_add_message_appends_and_sorts(self):
        base = datetime.utcnow()
        m1 = ConversationMessage(role="user", content="a", timestamp=base)
        m2 = ConversationMessage(
            role="assistant", content="b", timestamp=base + timedelta(seconds=1)
        )
        conv = Conversation(messages=[m1])
        conv.add_message(m2)
        assert len(conv.messages) == 2
        assert conv.messages[0].content == "a"
        assert conv.messages[1].content == "b"


# ---------------------------------------------------------------------------
# ConversationStore -- verify ABC constraints
# ---------------------------------------------------------------------------


class TestConversationStoreABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            ConversationStore()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# ConversationStoreManager
# ---------------------------------------------------------------------------


class TestConversationStoreManager:
    def test_creates_database_store_when_database_url_set(self):
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite://test.db"}, clear=True):
            manager = ConversationStoreManager()
            from api.storage.conversations import DatabaseConversationStore

            assert isinstance(manager._store, DatabaseConversationStore)

    def test_creates_database_store_in_production(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            manager = ConversationStoreManager()
            from api.storage.conversations import DatabaseConversationStore

            assert isinstance(manager._store, DatabaseConversationStore)

    def test_creates_database_store_in_staging(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=True):
            manager = ConversationStoreManager()
            from api.storage.conversations import DatabaseConversationStore

            assert isinstance(manager._store, DatabaseConversationStore)

    def test_falls_back_to_in_memory_in_development(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            manager = ConversationStoreManager()
            assert isinstance(manager._store, InMemoryConversationStore)

    def test_falls_back_to_in_memory_when_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            assert isinstance(manager._store, InMemoryConversationStore)

    @pytest.mark.asyncio
    async def test_delegates_save_and_get(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv = Conversation(user_id="u-1")
            await manager.save_conversation(conv)
            retrieved = await manager.get_conversation(conv.conversation_id)
            assert retrieved is not None
            assert retrieved.user_id == "u-1"

    @pytest.mark.asyncio
    async def test_delegates_delete(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv = Conversation(user_id="u-1")
            await manager.save_conversation(conv)
            deleted = await manager.delete_conversation(conv.conversation_id)
            assert deleted is True
            assert await manager.get_conversation(conv.conversation_id) is None

    @pytest.mark.asyncio
    async def test_delegates_delete_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            deleted = await manager.delete_conversation("nonexistent")
            assert deleted is False

    @pytest.mark.asyncio
    async def test_delegates_list(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv1 = Conversation(user_id="u-1", title="A")
            conv2 = Conversation(user_id="u-1", title="B")
            await manager.save_conversation(conv1)
            await manager.save_conversation(conv2)
            convs = await manager.list_conversations(user_id="u-1")
            assert len(convs) == 2

    @pytest.mark.asyncio
    async def test_delegates_update_title(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv = Conversation(user_id="u-1", title="Old")
            await manager.save_conversation(conv)
            ok = await manager.update_conversation_title(conv.conversation_id, "New")
            assert ok is True
            retrieved = await manager.get_conversation(conv.conversation_id)
            assert retrieved is not None
            assert retrieved.title == "New"

    @pytest.mark.asyncio
    async def test_delegates_update_title_nonexistent(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            ok = await manager.update_conversation_title("nonexistent", "Title")
            assert ok is False

    @pytest.mark.asyncio
    async def test_delegates_archive_messages(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            base = datetime.utcnow()
            m1 = ConversationMessage(role="user", content="old a", timestamp=base)
            m2 = ConversationMessage(
                role="assistant", content="new b", timestamp=base + timedelta(seconds=1)
            )
            conv = Conversation(user_id="u-1", messages=[m1, m2])
            await manager.save_conversation(conv)
            ok = await manager.archive_messages(
                conversation_id=conv.conversation_id,
                message_ids=[m1.message_id],
                summary_content="summary",
            )
            assert ok is True
            retrieved = await manager.get_conversation(conv.conversation_id)
            assert retrieved is not None
            assert len(retrieved.messages) == 2  # 1 archived message replaced by summary
            assert retrieved.messages[0].content == "summary"

    @pytest.mark.asyncio
    async def test_delegates_check_conversation_owner(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv = Conversation(user_id="u-1")
            await manager.save_conversation(conv)
            is_owner = await manager.check_conversation_owner(conv.conversation_id, "u-1")
            assert is_owner is True
            is_owner = await manager.check_conversation_owner(conv.conversation_id, "u-2")
            assert is_owner is False

    @pytest.mark.asyncio
    async def test_create_conversation(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv = await manager.create_conversation(user_id="u-1", title="New Chat")
            assert conv.user_id == "u-1"
            assert conv.title == "New Chat"
            # Should be persisted
            retrieved = await manager.get_conversation(conv.conversation_id)
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_create_conversation_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv = await manager.create_conversation()
            assert conv.title == "New Conversation"
            assert conv.user_id is None

    @pytest.mark.asyncio
    async def test_add_message_to_conversation(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv = await manager.create_conversation(user_id="u-1")
            ok = await manager.add_message_to_conversation(
                conversation_id=conv.conversation_id,
                role="user",
                content="test message",
            )
            assert ok is True
            retrieved = await manager.get_conversation(conv.conversation_id)
            assert retrieved is not None
            assert len(retrieved.messages) == 1
            assert retrieved.messages[0].content == "test message"
            assert retrieved.messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_add_message_to_conversation_nonexistent(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            ok = await manager.add_message_to_conversation(
                conversation_id="does-not-exist",
                role="user",
                content="test",
            )
            assert ok is False

    @pytest.mark.asyncio
    async def test_import_messages_to_conversation(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            conv = await manager.create_conversation(user_id="u-1")
            msgs = [
                ConversationMessage(role="user", content="one"),
                ConversationMessage(role="assistant", content="two"),
            ]
            ok = await manager.import_messages_to_conversation(conv.conversation_id, msgs)
            assert ok is True
            retrieved = await manager.get_conversation(conv.conversation_id)
            assert retrieved is not None
            assert len(retrieved.messages) == 2

    @pytest.mark.asyncio
    async def test_import_messages_to_conversation_nonexistent(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            ok = await manager.import_messages_to_conversation("nonexistent", [])
            assert ok is False

    @pytest.mark.asyncio
    async def test_import_messages_sorts_and_updates_timestamp(self):
        with patch.dict(os.environ, {}, clear=True):
            manager = ConversationStoreManager()
            base = datetime.utcnow()
            conv = await manager.create_conversation(user_id="u-1")
            ConversationMessage(role="system", content="preexisting", timestamp=base)
            await manager.add_message_to_conversation(
                conv.conversation_id,
                role="system",
                content="preexisting",
                timestamp=base,
            )
            later = ConversationMessage(
                role="user", content="later", timestamp=base + timedelta(seconds=5)
            )
            earlier = ConversationMessage(
                role="assistant",
                content="earlier",
                timestamp=base + timedelta(seconds=1),
            )
            ok = await manager.import_messages_to_conversation(
                conv.conversation_id, [later, earlier]
            )
            assert ok is True
            retrieved = await manager.get_conversation(conv.conversation_id)
            assert retrieved is not None
            # Order: existing, earlier, later
            assert retrieved.messages[0].content == "preexisting"
            assert retrieved.messages[1].content == "earlier"
            assert retrieved.messages[2].content == "later"
