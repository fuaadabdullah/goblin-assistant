"""
Conversation storage abstraction for Goblin Assistant
Provides persistent storage for chat conversations with database and in-memory backends
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import os
from sqlalchemy import select, delete, desc
from sqlalchemy.orm import selectinload

try:
    from .models import ConversationModel, MessageModel
    from .database import get_db, init_db
except ImportError:
    # Fallback for circular imports during initialization
    pass


class ConversationMessage:
    """Represents a single message in a conversation"""

    def __init__(
        self,
        role: str,
        content: str,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.role = role  # "user", "assistant", "system"
        self.content = content
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for storage"""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """Create message from dictionary"""
        return cls(
            message_id=data["message_id"],
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class Conversation:
    """Represents a conversation with multiple messages"""

    def __init__(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        messages: Optional[List[ConversationMessage]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.title = title or "New Conversation"
        self.messages = sorted(messages or [], key=lambda item: item.timestamp)
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.metadata = metadata or {}

    def add_message(self, message: ConversationMessage) -> None:
        """Add a message to the conversation"""
        self.messages.append(message)
        self.messages.sort(key=lambda item: item.timestamp)
        self.updated_at = max(self.updated_at, message.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary for storage"""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Create conversation from dictionary"""
        return cls(
            conversation_id=data["conversation_id"],
            user_id=data.get("user_id"),
            title=data.get("title", "New Conversation"),
            messages=[
                ConversationMessage.from_dict(msg) for msg in data.get("messages", [])
            ],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )


class ConversationStore(ABC):
    """Abstract base class for conversation storage"""

    @abstractmethod
    async def save_conversation(self, conversation: Conversation) -> None:
        """Save a conversation"""
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        pass

    @abstractmethod
    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Conversation]:
        """List conversations, optionally filtered by user"""
        pass

    @abstractmethod
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        pass


class InMemoryConversationStore(ConversationStore):
    """In-memory conversation storage for development/testing"""

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}

    async def save_conversation(self, conversation: Conversation) -> None:
        """Save a conversation to memory"""
        self._conversations[conversation.conversation_id] = conversation

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        return self._conversations.get(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Conversation]:
        """List conversations, optionally filtered by user"""
        conversations = list(self._conversations.values())

        if user_id:
            conversations = [c for c in conversations if c.user_id == user_id]

        # Sort by updated_at descending
        conversations.sort(key=lambda c: c.updated_at, reverse=True)

        return conversations[:limit]

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        if conversation_id in self._conversations:
            self._conversations[conversation_id].title = title
            self._conversations[conversation_id].updated_at = datetime.utcnow()
            return True
        return False


class DatabaseConversationStore(ConversationStore):
    """Database-backed conversation storage for production"""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv("DATABASE_URL")

    async def _ensure_initialized(self):
        """Ensure database tables exist"""
        await init_db()

    async def save_conversation(self, conversation: Conversation) -> None:
        """Save a conversation to database"""
        async with get_db() as session:
            # Check if conversation exists
            result = await session.execute(
                select(ConversationModel).where(
                    ConversationModel.conversation_id == conversation.conversation_id
                )
            )
            db_conversation = result.scalar_one_or_none()

            if not db_conversation:
                # Create new conversation
                db_conversation = ConversationModel(
                    conversation_id=conversation.conversation_id,
                    user_id=conversation.user_id,
                    title=conversation.title,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                    metadata_=conversation.metadata,
                )
                session.add(db_conversation)
            else:
                # Update existing
                db_conversation.title = conversation.title
                db_conversation.updated_at = conversation.updated_at
                db_conversation.metadata_ = conversation.metadata

            # Handle messages - sophisticated merge or replace strategy
            # For simplicity, we'll verify existing messages and add new ones
            # In a real high-throughput system, we might optimize this further

            # Flush to ensure conversation exists
            await session.flush()

            # Process messages
            for msg in conversation.messages:
                # Check if message exists
                msg_result = await session.execute(
                    select(MessageModel).where(
                        MessageModel.message_id == msg.message_id
                    )
                )
                db_msg = msg_result.scalar_one_or_none()

                if not db_msg:
                    new_msg = MessageModel(
                        message_id=msg.message_id,
                        conversation_id=conversation.conversation_id,
                        role=msg.role,
                        content=msg.content,
                        timestamp=msg.timestamp,
                        metadata_=msg.metadata,
                    )
                    session.add(new_msg)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID from database"""
        async with get_db() as session:
            result = await session.execute(
                select(ConversationModel)
                .where(ConversationModel.conversation_id == conversation_id)
                .options(selectinload(ConversationModel.messages))
            )
            db_conversation = result.scalar_one_or_none()

            if not db_conversation:
                return None

            # Convert to domain object
            messages = [
                ConversationMessage(
                    role=msg.role,
                    content=msg.content,
                    message_id=msg.message_id,
                    timestamp=msg.timestamp,
                    metadata=msg.metadata_,
                )
                for msg in sorted(db_conversation.messages, key=lambda item: item.timestamp)
            ]

            return Conversation(
                conversation_id=db_conversation.conversation_id,
                user_id=db_conversation.user_id,
                title=db_conversation.title,
                messages=messages,
                created_at=db_conversation.created_at,
                updated_at=db_conversation.updated_at,
                metadata=db_conversation.metadata_,
            )

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation from database"""
        async with get_db() as session:
            result = await session.execute(
                delete(ConversationModel).where(
                    ConversationModel.conversation_id == conversation_id
                )
            )
            return result.rowcount > 0

    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Conversation]:
        """List conversations from database"""
        async with get_db() as session:
            query = select(ConversationModel).order_by(
                desc(ConversationModel.updated_at)
            )

            if user_id:
                query = query.where(ConversationModel.user_id == user_id)

            query = query.limit(limit).options(selectinload(ConversationModel.messages))

            result = await session.execute(query)
            db_conversations = result.scalars().all()

            conversations = []
            for db_conv in db_conversations:
                # Convert messages
                messages = [
                    ConversationMessage(
                        role=msg.role,
                        content=msg.content,
                        message_id=msg.message_id,
                        timestamp=msg.timestamp,
                        metadata=msg.metadata_,
                    )
                    for msg in sorted(db_conv.messages, key=lambda item: item.timestamp)
                ]

                conversations.append(
                    Conversation(
                        conversation_id=db_conv.conversation_id,
                        user_id=db_conv.user_id,
                        title=db_conv.title,
                        messages=messages,
                        created_at=db_conv.created_at,
                        updated_at=db_conv.updated_at,
                        metadata=db_conv.metadata_,
                    )
                )

            return conversations

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title in database"""
        async with get_db() as session:
            result = await session.execute(
                select(ConversationModel).where(
                    ConversationModel.conversation_id == conversation_id
                )
            )
            db_conversation = result.scalar_one_or_none()

            if db_conversation:
                db_conversation.title = title
                db_conversation.updated_at = datetime.utcnow()
                return True
            return False


class ConversationStoreManager:
    """Manages conversation storage with environment-aware backend selection"""

    def __init__(self):
        self._store = self._create_store()

    def _create_store(self) -> ConversationStore:
        """Create appropriate store based on environment"""
        # Default to database store if DATABASE_URL is present, otherwise check environment
        if os.getenv("DATABASE_URL"):
            return DatabaseConversationStore()

        env = os.getenv("ENVIRONMENT", "development").lower()

        if env in ["production", "staging"]:
            return DatabaseConversationStore()
        else:
            # Fallback to in-memory for local dev without DB
            return InMemoryConversationStore()

    async def save_conversation(self, conversation: Conversation) -> None:
        """Save a conversation"""
        await self._store.save_conversation(conversation)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        return await self._store.get_conversation(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        return await self._store.delete_conversation(conversation_id)

    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Conversation]:
        """List conversations"""
        return await self._store.list_conversations(user_id, limit)

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        return await self._store.update_conversation_title(conversation_id, title)

    async def create_conversation(
        self, user_id: Optional[str] = None, title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation"""
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
        """Add a message to an existing conversation"""
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
        """Append existing messages to an existing conversation without rewriting IDs."""
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


# Global instance for easy access
conversation_store = ConversationStoreManager()
