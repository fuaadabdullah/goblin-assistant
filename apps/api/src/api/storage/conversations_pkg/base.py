from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import Conversation


class ConversationStore(ABC):
    """Abstract base class for conversation storage."""

    @abstractmethod
    async def save_conversation(self, conversation: Conversation) -> None: ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]: ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool: ...

    @abstractmethod
    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Conversation]: ...

    @abstractmethod
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool: ...

    @abstractmethod
    async def archive_messages(
        self,
        conversation_id: str,
        message_ids: List[str],
        summary_content: str,
        summary_metadata: Optional[Dict[str, Any]] = None,
        summary_message_id: Optional[str] = None,
        summary_timestamp: Optional[datetime] = None,
    ) -> bool: ...

    async def check_conversation_owner(
        self,
        conversation_id: str,
        user_id: str,
        db=None,
    ) -> bool:
        conv = await self.get_conversation(conversation_id)
        return conv is not None and conv.user_id == user_id
