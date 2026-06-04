"""
SQLAlchemy models for Goblin Assistant database storage
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

logger = logging.getLogger(__name__)

Base = declarative_base()


class UserModel(Base):
    """Database model for users"""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # For password-based auth
    google_id = Column(String, unique=True, nullable=True, index=True)  # For Google OAuth
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

    conversation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
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
        String,
        ForeignKey("messages.message_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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


class TaskModel(Base):
    """Database model for tasks"""

    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(
        String, nullable=False, default="pending"
    )  # pending, running, completed, failed
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
    privacy_settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("UserModel", foreign_keys=[user_id])


class DomainEventModel(Base):
    """Database model for typed orchestration/domain events."""

    __tablename__ = "domain_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False, index=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source = Column(String, nullable=False)
    actor_user_id = Column(String, nullable=True, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_domain_events_type_occurred", "event_type", "occurred_at"),
        Index("idx_domain_events_actor_occurred", "actor_user_id", "occurred_at"),
        Index("idx_domain_events_correlation", "correlation_id"),
    )


class ProviderSettingsModel(Base):
    """Persists dynamic provider config (e.g. Colab worker tunnel URL) across restarts."""

    __tablename__ = "provider_settings"

    provider_name = Column(String, primary_key=True)
    endpoint = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageEventModel(Base):
    """Append-only usage events for per-message billing and analytics."""

    __tablename__ = "usage_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(String, nullable=True, index=True)
    message_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=True, index=True)
    model = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_usage_events_user_created", "user_id", "created_at"),
        Index("idx_usage_events_conversation_created", "conversation_id", "created_at"),
    )


class UsageDailyAggregateModel(Base):
    """Daily usage rollups to support quotas and reporting."""

    __tablename__ = "usage_daily_aggregates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    usage_date = Column(Date, nullable=False, index=True)
    event_count = Column(Integer, nullable=False, default=0)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_usage_daily_user_date"),
        Index("idx_usage_daily_user_date", "user_id", "usage_date"),
    )


# Add vector relationships to existing models
def setup_vector_relationships():
    """Set up vector relationships after all models are imported"""

    # These relationships are already defined above, but we can ensure they're properly set up
    # The vector_models.py file defines the back_populates relationships

    from . import vector_models  # noqa: F401

    _ = vector_models.EmbeddingModel

    # Check if relationships exist and are properly configured
    try:
        # Test relationship access
        _ = UserModel.embeddings
        _ = UserModel.memory_facts
        _ = ConversationModel.embeddings
        _ = ConversationModel.summary
        logger.info("Vector relationships successfully configured")
    except Exception as e:
        logger.warning("Vector relationship setup issue: %s", e)


setup_vector_relationships()
