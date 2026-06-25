import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


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
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
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
        last_accessed: Optional[datetime] = None,
    ):
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.title = title or "New Conversation"
        self.messages = sorted(messages or [], key=lambda item: item.timestamp)
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_accessed = last_accessed or datetime.utcnow()
        self.metadata = metadata or {}

    def add_message(self, message: ConversationMessage) -> None:
        self.messages.append(message)
        self.messages.sort(key=lambda item: item.timestamp)
        self.updated_at = max(self.updated_at, message.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        return cls(
            conversation_id=data["conversation_id"],
            user_id=data.get("user_id"),
            title=data.get("title", "New Conversation"),
            messages=[ConversationMessage.from_dict(msg) for msg in data.get("messages", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            last_accessed=datetime.fromisoformat(
                data.get("last_accessed", datetime.utcnow().isoformat())
            ),
            metadata=data.get("metadata", {}),
        )
