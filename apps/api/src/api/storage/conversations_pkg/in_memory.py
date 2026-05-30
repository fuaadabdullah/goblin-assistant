from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import ConversationStore
from .models import Conversation, ConversationMessage


class InMemoryConversationStore(ConversationStore):
    """In-memory conversation storage for development/testing with TTL eviction."""

    def __init__(self, max_conversations: int = 1000, ttl_seconds: int = 3600):
        self._conversations: Dict[str, Conversation] = {}
        self.max_conversations = max_conversations
        self.ttl_seconds = ttl_seconds

    def _evict_expired(self) -> None:
        now = datetime.utcnow()
        ttl_threshold = now.timestamp() - self.ttl_seconds

        expired_ids = [
            conv_id
            for conv_id, conv in self._conversations.items()
            if conv.last_accessed.timestamp() < ttl_threshold
        ]
        for conv_id in expired_ids:
            del self._conversations[conv_id]

        if len(self._conversations) > self.max_conversations:
            sorted_conversations = sorted(
                self._conversations.items(),
                key=lambda item: item[1].last_accessed.timestamp(),
            )
            num_to_remove = len(self._conversations) - self.max_conversations
            for conv_id, _ in sorted_conversations[:num_to_remove]:
                del self._conversations[conv_id]

    async def save_conversation(self, conversation: Conversation) -> None:
        conversation.last_accessed = datetime.utcnow()
        self._conversations[conversation.conversation_id] = conversation
        self._evict_expired()

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        if conversation_id in self._conversations:
            self._conversations[conversation_id].last_accessed = datetime.utcnow()
            self._evict_expired()
            return self._conversations[conversation_id]
        return None

    async def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Conversation]:
        self._evict_expired()
        conversations = list(self._conversations.values())
        if user_id:
            conversations = [c for c in conversations if c.user_id == user_id]
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations[:limit]

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        if conversation_id in self._conversations:
            self._conversations[conversation_id].title = title
            self._conversations[conversation_id].updated_at = datetime.utcnow()
            self._conversations[conversation_id].last_accessed = datetime.utcnow()
            self._evict_expired()
            return True
        return False

    async def archive_messages(
        self,
        conversation_id: str,
        message_ids: List[str],
        summary_content: str,
        summary_metadata: Optional[Dict[str, Any]] = None,
        summary_message_id: Optional[str] = None,
        summary_timestamp: Optional[datetime] = None,
    ) -> bool:
        conversation = self._conversations.get(conversation_id)
        if not conversation or not message_ids:
            return False

        archive_set = set(message_ids)
        archived = [msg for msg in conversation.messages if msg.message_id in archive_set]
        if not archived:
            return False

        retained = [msg for msg in conversation.messages if msg.message_id not in archive_set]
        summary_ts = summary_timestamp or max(msg.timestamp for msg in archived)
        summary_message = ConversationMessage(
            role="system",
            content=summary_content,
            metadata=summary_metadata or {},
            message_id=summary_message_id,
            timestamp=summary_ts,
        )
        retained.append(summary_message)
        retained.sort(key=lambda item: item.timestamp)

        conversation.messages = retained
        conversation.updated_at = max(conversation.updated_at, summary_ts)
        conversation.last_accessed = datetime.utcnow()
        self._conversations[conversation_id] = conversation
        self._evict_expired()
        return True

    async def check_conversation_owner(
        self,
        conversation_id: str,
        user_id: str,
        db=None,
    ) -> bool:
        self._evict_expired()
        conv = self._conversations.get(conversation_id)
        return conv is not None and conv.user_id == user_id
