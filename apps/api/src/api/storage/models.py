"""
SQLAlchemy models for Goblin Assistant database storage
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Boolean, Integer, text
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime

Base = declarative_base()


class UserModel(Base):
    """Database model for users"""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # For password-based auth
    google_id = Column(
        String, unique=True, nullable=True, index=True
    )  # For Google OAuth
    passkey_credential_id = Column(String, unique=True, nullable=True)  # For WebAuthn
    passkey_public_key = Column(Text, nullable=True)  # For WebAuthn
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, server_default=text("1"))

    # Relationships
    conversations = relationship(
        "ConversationModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    # Vector relationships
    embeddings = relationship(
        "EmbeddingModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    memory_facts = relationship(
        "MemoryFactModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class ConversationModel(Base):
    """Database model for conversations"""

    __tablename__ = "conversations"

    conversation_id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_ = Column("metadata", JSON, default=dict)

    # Relationships
    user = relationship("UserModel", back_populates="conversations")
    messages = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.timestamp",
    )
    
    # Vector relationships
    embeddings = relationship(
        "EmbeddingModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    summary = relationship(
        "ConversationSummaryModel",
        back_populates="conversation",
        uselist=False,
        cascade="all, delete-orphan",
    )


class MessageModel(Base):
    """Database model for chat messages"""

    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String, ForeignKey("conversations.conversation_id"), nullable=False, index=True
    )
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSON, default=dict)

    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")
    attachments = relationship(
        "MessageAttachmentModel",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="MessageAttachmentModel.created_at",
    )


class MessageAttachmentModel(Base):
    """Database model for message file attachments"""

    __tablename__ = "message_attachments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(
        String, ForeignKey("messages.message_id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_key = Column(String, nullable=False)  # S3 key or local path
    upload_hash = Column(String, nullable=True)  # SHA256 for dedup
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    message = relationship("MessageModel", back_populates="attachments")


# Import vector models to ensure relationships are properly set up
from .vector_models import EmbeddingModel, ConversationSummaryModel, MemoryFactModel


class TaskModel(Base):
    """Database model for tasks"""

    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, failed
    task_type = Column(String, nullable=True)  # Type of task (e.g., "chat", "analysis", etc.)
    payload = Column(JSON, default=dict)  # Task input data
    result = Column(JSON, nullable=True)  # Task output data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_ = Column("metadata", JSON, default=dict)

    # Relationship
    user = relationship("UserModel", foreign_keys=[user_id])


class UserSessionModel(Base):
    """Database model for persistent user sessions (survives server restarts)"""

    __tablename__ = "user_sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("UserModel", foreign_keys=[user_id])


class UserPreferencesModel(Base):
    """Database model for user preferences"""

    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    default_provider = Column(String, nullable=True)
    default_model = Column(String, nullable=True)
    rag_consent = Column(String, default="false")  # Using string for SQLite compatibility
    ui_preferences = Column(JSON, default=dict)
    privacy_settings = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("UserModel", foreign_keys=[user_id])


class SupportTicketModel(Base):
    """Database model for support tickets."""

    __tablename__ = "support_tickets"

    ticket_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String, nullable=True)
    category = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    status = Column(String, nullable=False, default="received")
    subject = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    attachment_url = Column(String, nullable=True)
    triage = Column(JSON, default=dict)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserModel", foreign_keys=[user_id])


class NotificationModel(Base):
    """Database model for in-app notifications."""

    __tablename__ = "notifications"

    notification_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    channel = Column(String, nullable=False, default="in_app")
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("UserModel", foreign_keys=[user_id])


class ChatSettingsModel(Base):
    """Database model for per-user chat settings."""

    __tablename__ = "chat_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    default_provider = Column(String, nullable=True)
    default_model = Column(String, nullable=True)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(String, nullable=True)  # stored as string for SQLite compatibility
    max_tokens = Column(Integer, nullable=True)
    summary_enabled = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, default=dict)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("UserModel", foreign_keys=[user_id])


class ApiKeyModel(Base):
    """Database model for user API keys."""

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=True)
    key_hash = Column(String, nullable=True)
    key_prefix = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserModel", foreign_keys=[user_id])


class FeatureFlagModel(Base):
    """Database model for feature flags."""

    __tablename__ = "feature_flags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    flag_key = Column(String, nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=True)
    default_value = Column(JSON, nullable=True)
    user_overrides = Column(JSON, default=dict)
    rollout_percent = Column(String, nullable=True)  # stored as string for SQLite compatibility
    target_users = Column(JSON, default=list)
    target_roles = Column(JSON, default=list)
    metadata_ = Column("metadata", JSON, default=dict)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GlobalSettingModel(Base):
    """Database model for global platform settings."""

    __tablename__ = "global_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProviderSettingsModel(Base):
    """Database model for provider runtime settings."""

    __tablename__ = "provider_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_name = Column(String, nullable=False, unique=True, index=True)
    endpoint = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    weight = Column(String, nullable=True)  # stored as string for SQLite compatibility
    base_url = Column(String, nullable=True)
    models = Column(JSON, default=list)
    api_key_encrypted = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Add vector relationships to existing models
def setup_vector_relationships():
    """Set up vector relationships after all models are imported"""
    
    # These relationships are already defined above, but we can ensure they're properly set up
    # The vector_models.py file defines the back_populates relationships
    
    # Check if relationships exist and are properly configured
    try:
        # Test relationship access
        _ = UserModel.embeddings
        _ = UserModel.memory_facts
        _ = ConversationModel.embeddings
        _ = ConversationModel.summary
        print("Vector relationships successfully configured")
    except Exception as e:
        print(f"Warning: Vector relationship setup issue: {e}")
