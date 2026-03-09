"""
SQLAlchemy models for Goblin Assistant database storage
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Boolean, text
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