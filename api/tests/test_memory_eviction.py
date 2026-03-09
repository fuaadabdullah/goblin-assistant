"""
Unit tests for InMemoryConversationStore TTL eviction and max-size enforcement.

Tests cover:
- TTL eviction removes expired conversations
- Max-size enforcement removes oldest conversations when limit exceeded
- Access timestamp updates on get/save operations
- Lazy eviction on operations
"""

import pytest
from datetime import datetime, timedelta
from api.storage.conversations import (
    InMemoryConversationStore,
    Conversation,
    ConversationMessage,
)


@pytest.fixture
def memory_store_short_ttl():
    """Create an in-memory store with short TTL for testing (10 seconds)"""
    return InMemoryConversationStore(max_conversations=5, ttl_seconds=10)


@pytest.fixture
def memory_store_default():
    """Create an in-memory store with default settings"""
    return InMemoryConversationStore()


@pytest.mark.asyncio
async def test_ttl_eviction_removes_expired_conversations(memory_store_short_ttl):
    """Test that conversations older than TTL are removed on eviction"""
    store = memory_store_short_ttl
    
    # Create a conversation
    conv = Conversation(user_id="user1", title="Old Conversation")
    await store.save_conversation(conv)
    conv_id = conv.conversation_id
    
    # Verify it exists
    retrieved = await store.get_conversation(conv_id)
    assert retrieved is not None
    
    # Manually set last_accessed to old timestamp (11 seconds ago)
    old_time = (datetime.utcnow() - timedelta(seconds=11))
    store._conversations[conv_id].last_accessed = old_time
    
    # Trigger eviction by listing conversations
    conversations = await store.list_conversations()
    
    # Verify conversation was evicted
    assert conv_id not in store._conversations
    assert len(conversations) == 0


@pytest.mark.asyncio
async def test_max_size_eviction_removes_oldest(memory_store_short_ttl):
    """Test that when max is exceeded, oldest accessed conversations are removed"""
    store = memory_store_short_ttl
    max_size = store.max_conversations
    
    # Create conversations beyond max
    conv_ids = []
    for i in range(max_size + 2):
        conv = Conversation(user_id=f"user_{i}", title=f"Conv {i}")
        conv.last_accessed = datetime.utcnow() - timedelta(seconds=i)
        await store.save_conversation(conv)
        conv_ids.append(conv.conversation_id)
    
    # After eviction, should only have max_size conversations
    assert len(store._conversations) <= max_size
    
    # Oldest conversations should be removed
    # Conversations created first (index 0, 1) should be removed
    assert conv_ids[0] not in store._conversations
    assert conv_ids[1] not in store._conversations


@pytest.mark.asyncio
async def test_last_accessed_updates_on_save(memory_store_default):
    """Test that last_accessed timestamp is updated when conversation is saved"""
    store = memory_store_default
    
    conv = Conversation(user_id="user1", title="Test")
    old_time = datetime.utcnow() - timedelta(hours=1)
    conv.last_accessed = old_time
    
    # Save the conversation
    await store.save_conversation(conv)
    
    # last_accessed should be updated to now
    stored = store._conversations[conv.conversation_id]
    assert stored.last_accessed > old_time
    assert (stored.last_accessed - datetime.utcnow()).total_seconds() < 1  # within 1 second


@pytest.mark.asyncio
async def test_last_accessed_updates_on_get(memory_store_default):
    """Test that last_accessed timestamp is updated when conversation is retrieved"""
    store = memory_store_default
    
    conv = Conversation(user_id="user1", title="Test")
    await store.save_conversation(conv)
    conv_id = conv.conversation_id
    
    # Manually set to old time
    old_time = datetime.utcnow() - timedelta(hours=1)
    store._conversations[conv_id].last_accessed = old_time
    
    # Retrieve the conversation
    retrieved = await store.get_conversation(conv_id)
    
    # last_accessed should be updated
    assert retrieved is not None
    assert retrieved.last_accessed > old_time
    assert (retrieved.last_accessed - datetime.utcnow()).total_seconds() < 1


@pytest.mark.asyncio
async def test_last_accessed_updates_on_update_title(memory_store_default):
    """Test that last_accessed is updated when conversation title is updated"""
    store = memory_store_default
    
    conv = Conversation(user_id="user1", title="Old Title")
    await store.save_conversation(conv)
    conv_id = conv.conversation_id
    
    # Set to old time
    old_time = datetime.utcnow() - timedelta(hours=1)
    store._conversations[conv_id].last_accessed = old_time
    
    # Update title
    result = await store.update_conversation_title(conv_id, "New Title")
    
    assert result is True
    updated = store._conversations[conv_id]
    assert updated.title == "New Title"
    assert updated.last_accessed > old_time


@pytest.mark.asyncio
async def test_eviction_called_on_list(memory_store_short_ttl):
    """Test that eviction is triggered when listing conversations"""
    store = memory_store_short_ttl
    
    # Create conversations
    conv1 = Conversation(user_id="user1", title="Fresh")
    conv2 = Conversation(user_id="user1", title="Old")
    
    await store.save_conversation(conv1)
    await store.save_conversation(conv2)
    
    # Make conv2 expired
    store._conversations[conv2.conversation_id].last_accessed = (
        datetime.utcnow() - timedelta(seconds=11)
    )
    
    # List conversations should trigger eviction
    conversations = await store.list_conversations(user_id="user1")
    
    # Only fresh conversation should remain
    assert len(conversations) == 1
    assert conversations[0].conversation_id == conv1.conversation_id


@pytest.mark.asyncio
async def test_delete_conversation_works(memory_store_default):
    """Test that delete operation removes conversations"""
    store = memory_store_default
    
    conv = Conversation(user_id="user1", title="To Delete")
    await store.save_conversation(conv)
    conv_id = conv.conversation_id
    
    # Verify exists
    assert conv_id in store._conversations
    
    # Delete
    result = await store.delete_conversation(conv_id)
    
    assert result is True
    assert conv_id not in store._conversations


@pytest.mark.asyncio
async def test_get_conversation_returns_none_for_missing(memory_store_default):
    """Test that get returns None for non-existent conversations"""
    store = memory_store_default
    
    result = await store.get_conversation("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_user_filtering_with_eviction(memory_store_default):
    """Test that user filtering still works with eviction"""
    store = memory_store_default
    
    # Create conversations for different users
    conv1 = Conversation(user_id="user1", title="User1 Conv")
    conv2 = Conversation(user_id="user2", title="User2 Conv")
    conv3 = Conversation(user_id="user1", title="User1 Conv 2")
    
    await store.save_conversation(conv1)
    await store.save_conversation(conv2)
    await store.save_conversation(conv3)
    
    # List for user1
    user1_convs = await store.list_conversations(user_id="user1")
    
    assert len(user1_convs) == 2
    assert all(c.user_id == "user1" for c in user1_convs)
    
    # List for user2
    user2_convs = await store.list_conversations(user_id="user2")
    
    assert len(user2_convs) == 1
    assert user2_convs[0].user_id == "user2"
