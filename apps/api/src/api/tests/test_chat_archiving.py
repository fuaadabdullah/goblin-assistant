import asyncio
from datetime import datetime, timedelta
import uuid

import pytest

from api.storage.conversations import (
    Conversation,
    ConversationMessage,
    conversation_store,
)


@pytest.mark.asyncio
async def test_maybe_archive_skips_below_threshold(monkeypatch):
    from api.chat_router import archiving

    conv = await conversation_store.create_conversation(user_id="user-1", title="Short")
    for i in range(3):
        await conversation_store.add_message_to_conversation(
            conversation_id=conv.conversation_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"msg-{i}",
        )

    monkeypatch.setattr(archiving, "CHAT_ARCHIVE_THRESHOLD", 10)
    monkeypatch.setattr(archiving, "CHAT_ARCHIVE_RETAIN_LAST", 2)

    called = {"archive": False}

    async def fake_archive_messages(**kwargs):
        called["archive"] = True
        return True

    monkeypatch.setattr(
        "api.chat_router.conversation_store.archive_messages",
        fake_archive_messages,
    )

    await archiving._maybe_archive_conversation(conv.conversation_id)
    assert called["archive"] is False


@pytest.mark.asyncio
async def test_maybe_archive_replaces_older_messages_with_summary(monkeypatch):
    from api.chat_router import archiving

    conv_id = "archive-conv-1"
    base = datetime.utcnow()
    messages = [
        ConversationMessage(role="user", content="u1", timestamp=base - timedelta(minutes=5)),
        ConversationMessage(role="assistant", content="a1", timestamp=base - timedelta(minutes=4)),
        ConversationMessage(role="user", content="u2", timestamp=base - timedelta(minutes=3)),
        ConversationMessage(role="assistant", content="a2", timestamp=base - timedelta(minutes=2)),
        ConversationMessage(role="user", content="u3", timestamp=base - timedelta(minutes=1)),
        ConversationMessage(role="assistant", content="a3", timestamp=base),
    ]
    conv = Conversation(
        conversation_id=conv_id,
        user_id="user-1",
        title="Archiveable",
        messages=messages,
    )
    await conversation_store.save_conversation(conv)

    monkeypatch.setattr(archiving, "CHAT_ARCHIVE_THRESHOLD", 6)
    monkeypatch.setattr(archiving, "CHAT_ARCHIVE_RETAIN_LAST", 2)

    async def fake_invoke_provider(pid, model, payload, timeout_ms, stream=False):
        return {
            "ok": True,
            "provider": pid or "auto",
            "model": model,
            "result": {"text": "Summary of archived segment."},
        }

    monkeypatch.setattr("api.chat_router.invoke_provider", fake_invoke_provider)

    await archiving._maybe_archive_conversation(conv_id)

    updated = await conversation_store.get_conversation(conv_id)
    assert updated is not None
    assert len(updated.messages) == 3
    summary = updated.messages[0]
    assert summary.metadata.get("archived_summary") is True
    assert summary.metadata.get("archived_message_count") == 4
    assert summary.metadata.get("archive_window_start")
    assert summary.metadata.get("archive_window_end")
    assert [m.content for m in updated.messages[1:]] == ["u3", "a3"]


@pytest.mark.asyncio
async def test_schedule_archive_is_non_blocking_when_archive_fails(monkeypatch):
    from api.chat_router import archiving

    async def explode(_conversation_id: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(archiving, "_maybe_archive_conversation", explode)

    await archiving.schedule_conversation_archive("conv-any")
    await asyncio.sleep(0.05)

    # If schedule were blocking/fatal, the test would fail with exception above.
    assert "conv-any" not in archiving._archive_inflight


@pytest.mark.asyncio
async def test_database_archive_messages_replaces_rows_transactionally():
    from api.storage.conversations import DatabaseConversationStore
    from api.storage.database import init_db

    await init_db()
    store = DatabaseConversationStore()
    conv_id = f"db-archive-{uuid.uuid4()}"
    base = datetime.utcnow()

    conv = Conversation(
        conversation_id=conv_id,
        user_id="user-db",
        title="DB Archive",
        messages=[
            ConversationMessage(
                role="user", content="old-u", timestamp=base - timedelta(minutes=3)
            ),
            ConversationMessage(
                role="assistant", content="old-a", timestamp=base - timedelta(minutes=2)
            ),
            ConversationMessage(
                role="user", content="new-u", timestamp=base - timedelta(minutes=1)
            ),
        ],
    )
    await store.save_conversation(conv)

    archive_ids = [conv.messages[0].message_id, conv.messages[1].message_id]
    ok = await store.archive_messages(
        conversation_id=conv_id,
        message_ids=archive_ids,
        summary_content="Archived DB summary",
        summary_metadata={"archived_summary": True, "archived_message_count": 2},
        summary_timestamp=base - timedelta(minutes=2),
    )
    assert ok is True

    updated = await store.get_conversation(conv_id)
    assert updated is not None
    assert len(updated.messages) == 2
    assert updated.messages[0].content == "Archived DB summary"
    assert updated.messages[0].metadata.get("archived_summary") is True
    assert updated.messages[1].content == "new-u"

    await store.delete_conversation(conv_id)
