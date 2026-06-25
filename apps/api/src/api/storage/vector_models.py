"""
Vector storage models for semantic retrieval using pgvector
"""

import os
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .models import Base, ConversationModel, UserModel

# Check if we should use pgvector or fallback to Text
# Default to false because some environments (like the current one) don't have the extension
USE_PGVECTOR = os.getenv("USE_PGVECTOR", "true").lower() == "true"

if USE_PGVECTOR:
    try:
        from pgvector.sqlalchemy import Vector as VectorType
    except ImportError:
        USE_PGVECTOR = False

if not USE_PGVECTOR:
    # Use Text as fallback, ensure it evaluates to TEXT in SQL
    class VectorType(Text):
        def __init__(self, size=None, **kwargs):
            super().__init__(**kwargs)
            self.size = size

        def __repr__(self):
            return "TEXT"

        def get_col_spec(self, **_kw):
            return "TEXT"


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
    embedding = Column(VectorType(1536))  # OpenAI text-embedding-3-small dimension
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
    summary_embedding = Column(VectorType(1536))
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
    fact_embedding = Column(VectorType(1536))
    category = Column(String, nullable=True)  # e.g., "preferences", "knowledge", "tasks"
    memory_type = Column(String, nullable=True, index=True)
    source_kind = Column(String, nullable=True, index=True)
    source_id = Column(String, nullable=True, index=True)
    salience_score = Column(Float, nullable=True, default=0.0, index=True)
    confidence = Column(Float, nullable=True, default=0.0)
    memory_state = Column(String, nullable=False, default="active", index=True)
    sensitivity_level = Column(String, nullable=True, default="low")
    retention_days = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    last_accessed_at = Column(DateTime, nullable=True, index=True)
    confirmation_count = Column(Integer, nullable=True, default=0)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    related_memory_ids = Column(JSON, default=list)
    entity_refs = Column(JSON, default=list)
    metadata_ = Column("metadata", JSON, default=dict)
    scope = Column(String, nullable=True, default="global", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("UserModel", back_populates="memory_facts")

    # Indexes
    __table_args__ = (
        Index("idx_memory_facts_user_id", "user_id"),
        Index("idx_memory_facts_category", "category"),
        Index("idx_memory_facts_memory_type", "memory_type"),
        Index("idx_memory_facts_salience_score", "salience_score"),
        Index("idx_memory_facts_expires_at", "expires_at"),
        Index("idx_memory_facts_scope", "scope"),
    )


class MemoryEntityModel(Base):
    """Typed entity nodes in the memory knowledge graph."""

    __tablename__ = "memory_entities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_value = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    scope = Column(String, nullable=True, default="global")
    confidence = Column(Float, nullable=True, default=1.0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("UserModel", back_populates="memory_entities")

    __table_args__ = (
        Index("idx_memory_entities_user_id", "user_id"),
        Index("idx_memory_entities_user_type", "user_id", "entity_type"),
        Index("idx_memory_entities_entity_value", "entity_value"),
    )


class MemoryEntityRelationModel(Base):
    """Typed relation edges between entity nodes in the memory graph."""

    __tablename__ = "memory_entity_relations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source_entity_id = Column(String, ForeignKey("memory_entities.id"), nullable=False)
    target_entity_id = Column(String, ForeignKey("memory_entities.id"), nullable=False)
    relation_type = Column(String, nullable=False)
    memory_fact_id = Column(String, ForeignKey("memory_facts.id"), nullable=True)
    confidence = Column(Float, nullable=True, default=1.0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    source_entity = relationship(
        "MemoryEntityModel", foreign_keys=[source_entity_id], back_populates="source_relations"
    )
    target_entity = relationship(
        "MemoryEntityModel", foreign_keys=[target_entity_id], back_populates="target_relations"
    )

    __table_args__ = (
        Index("idx_entity_relations_user_id", "user_id"),
        Index("idx_entity_relations_source", "source_entity_id", "relation_type"),
        Index("idx_entity_relations_target", "target_entity_id", "relation_type"),
        Index("idx_entity_relations_fact", "memory_fact_id"),
    )


# Add relationships to existing models
def add_vector_relationships():
    """Add vector relationships to existing models"""
    if not hasattr(UserModel, "embeddings"):
        UserModel.embeddings = relationship(
            "EmbeddingModel",
            back_populates="user",
            cascade="all, delete-orphan",
        )
    if not hasattr(UserModel, "memory_facts"):
        UserModel.memory_facts = relationship(
            "MemoryFactModel",
            back_populates="user",
            cascade="all, delete-orphan",
        )
    if not hasattr(UserModel, "memory_entities"):
        UserModel.memory_entities = relationship(
            "MemoryEntityModel",
            back_populates="user",
            cascade="all, delete-orphan",
        )

    if not hasattr(MemoryEntityModel, "source_relations"):
        MemoryEntityModel.source_relations = relationship(
            "MemoryEntityRelationModel",
            foreign_keys="MemoryEntityRelationModel.source_entity_id",
            back_populates="source_entity",
            cascade="all, delete-orphan",
        )
    if not hasattr(MemoryEntityModel, "target_relations"):
        MemoryEntityModel.target_relations = relationship(
            "MemoryEntityRelationModel",
            foreign_keys="MemoryEntityRelationModel.target_entity_id",
            back_populates="target_entity",
            cascade="all, delete-orphan",
        )

    if not hasattr(ConversationModel, "embeddings"):
        ConversationModel.embeddings = relationship(
            "EmbeddingModel",
            back_populates="conversation",
            cascade="all, delete-orphan",
        )
    if not hasattr(ConversationModel, "summary"):
        ConversationModel.summary = relationship(
            "ConversationSummaryModel",
            back_populates="conversation",
            uselist=False,
            cascade="all, delete-orphan",
        )


# Ensure back_populates relationships are available as soon as the module is imported.
add_vector_relationships()
