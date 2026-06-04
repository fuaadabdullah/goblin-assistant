import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import ConversationStore
from .database import DatabaseConversationStore
from .in_memory import InMemoryConversationStore
from .models import Conversation, ConversationMessage


class ConversationStoreManager:
    """Manages conversation storage with environment-aware backend selection."""

    def __init__(self):
        self._store = self._create_store()

    def _create_store(self) -> ConversationStore:
        if os.getenv("DATABASE_URL"):
            return DatabaseConversationStore()

        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ["production", "staging"]:
            return DatabaseConversationStore()
        return InMemoryConversationStore()

    async def save_conversation(self, conversation: Conversation) -> None:
        await self._store.save_conversation(conversation)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return await self._store.get_conversation(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        return await self._store.delete_conversation(conversation_id)

    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Conversation]:
        return await self._store.list_conversations(user_id, limit)

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        return await self._store.update_conversation_title(conversation_id, title)

    async def archive_messages(
        self,
        conversation_id: str,
        message_ids: List[str],
        summary_content: str,
        summary_metadata: Optional[Dict[str, Any]] = None,
        summary_message_id: Optional[str] = None,
        summary_timestamp: Optional[datetime] = None,
    ) -> bool:
        return await self._store.archive_messages(
            conversation_id=conversation_id,
            message_ids=message_ids,
            summary_content=summary_content,
            summary_metadata=summary_metadata,
            summary_message_id=summary_message_id,
            summary_timestamp=summary_timestamp,
        )

    async def check_conversation_owner(
        self,
        conversation_id: str,
        user_id: str,
        db=None,
    ) -> bool:
        return await self._store.check_conversation_owner(conversation_id, user_id, db=db)

    async def create_conversation(
        self, user_id: Optional[str] = None, title: Optional[str] = None
    ) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        await self.save_conversation(conversation)
        return conversation

    async def add_message_to_conversation(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata,
            message_id=message_id,
            timestamp=timestamp,
        )
        conversation.add_message(message)
        await self.save_conversation(conversation)
        return True

    async def import_messages_to_conversation(
        self,
        conversation_id: str,
        messages: List[ConversationMessage],
    ) -> bool:
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        for message in messages:
            conversation.messages.append(message)

        conversation.messages.sort(key=lambda item: item.timestamp)

        if messages:
            latest_timestamp = max(message.timestamp for message in messages)
            conversation.updated_at = max(conversation.updated_at, latest_timestamp)

        await self.save_conversation(conversation)
        return True


conversation_store = ConversationStoreManager()
