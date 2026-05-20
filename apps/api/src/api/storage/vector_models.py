"""
Vector storage models for semantic retrieval using pgvector
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Index
from sqlalchemy.orm import declarative_base, relationship
import os
import uuid
from datetime import datetime

# Check if we should use pgvector or fallback to Text
# Default to false because some environments (like the current one) don't have the extension
USE_PGVECTOR = os.getenv("USE_PGVECTOR", "false").lower() == "true"

if USE_PGVECTOR:
    try:
        from pgvector.sqlalchemy import Vector as VECTOR
    except ImportError:
        USE_PGVECTOR = False

if not USE_PGVECTOR:
    # Use Text as fallback, ensure it evaluates to TEXT in SQL
    class VECTOR(Text):
        def __init__(self, size=None, **kwargs):
            super().__init__(**kwargs)
            self.size = size

        def __repr__(self):
            return "TEXT"

        def get_col_spec(self, **kw):
            return "TEXT"


# Use the shared Base from models.py to ensure all models are in the same registry
from .models import Base


class EmbeddingModel(Base):
    """Vector embeddings table for semantic search"""

    __tablename__ = "embeddings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    conversation_id = Column(
        String, ForeignKey("conversations.conversation_id"), nullable=True, index=True
    )
    source_type = Column(String, nullable=False)  # message, summary, task, memory
    source_id = Column(String, nullable=False)
    embedding = Column(VECTOR(1536))  # OpenAI text-embedding-3-small dimension
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("UserModel", back_populates="embeddings")
    conversation = relationship("ConversationModel", back_populates="embeddings")

    # Custom indexes for pgvector
    __table_args__ = (
        Index("idx_embeddings_user_conversation", "user_id", "conversation_id"),
        Index("idx_embeddings_source_type", "source_type"),
        Index("idx_embeddings_created_at", "created_at"),
    )


class ConversationSummaryModel(Base):
    """Conversation summaries with embeddings for efficient retrieval"""

    __tablename__ = "conversation_summaries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String,
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_text = Column(Text, nullable=False)
    summary_embedding = Column(VECTOR(1536))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    conversation = relationship("ConversationModel", back_populates="summary")


class MemoryFactModel(Base):
    """Long-term memory facts with embeddings"""

    __tablename__ = "memory_facts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    fact_text = Column(Text, nullable=False)
    fact_embedding = Column(VECTOR(1536))
    category = Column(
        String, nullable=True
    )  # e.g., "preferences", "knowledge", "tasks"
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("UserModel", back_populates="memory_facts")

    # Indexes
    __table_args__ = (
        Index("idx_memory_facts_user_id", "user_id"),
        Index("idx_memory_facts_category", "category"),
    )


# Add relationships to existing models
def add_vector_relationships():
    """Add vector relationships to existing models"""

    # Add to UserModel
    from .models import UserModel

    UserModel.embeddings = relationship(
        "EmbeddingModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    UserModel.memory_facts = relationship(
        "MemoryFactModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Add to ConversationModel
    from .models import ConversationModel

    ConversationModel.embeddings = relationship(
        "EmbeddingModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    ConversationModel.summary = relationship(
        "ConversationSummaryModel",
        back_populates="conversation",
        uselist=False,
        cascade="all, delete-orphan",
    )
