"""
Enhanced memory models for memory stratification system
Adds memory_items table and enhanced metadata tracking
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Index, Integer, Float
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime

# Try to import VECTOR for PostgreSQL, fallback to Text for SQLite
try:
    from sqlalchemy.dialects.postgresql import VECTOR
except ImportError:
    # Fallback for SQLite or when pgvector is not available
    from sqlalchemy import Text as VECTOR

Base = declarative_base()


class MemoryItemModel(Base):
    """Enhanced memory items table with promotion tracking"""
    
    __tablename__ = "memory_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    fact_text = Column(Text, nullable=False)
    fact_embedding = Column(VECTOR(1536))
    category = Column(String, nullable=True)  # user_trait, preference, skill, goal, constraint, context
    confidence = Column(Float, nullable=False, default=0.0)
    source_type = Column(String, nullable=False)  # fact_message, preference_message, summary, manual
    source_id = Column(String, nullable=True)  # ID of source (conversation_id, summary_id, etc.)
    metadata_ = Column("metadata", JSON, default=dict)
    
    # Promotion tracking
    promotion_status = Column(String, default="promoted")  # promoted, rejected, duplicate
    promotion_reason = Column(Text, nullable=True)
    promotion_confidence = Column(Float, nullable=True)
    consistency_score = Column(Float, nullable=True)
    
    # Lifecycle tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_confirmed = Column(DateTime, nullable=True)
    confirmation_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("UserModel", back_populates="memory_items")

    # Indexes
    __table_args__ = (
        Index("idx_memory_items_user_category", "user_id", "category"),
        Index("idx_memory_items_confidence", "confidence"),
        Index("idx_memory_items_promotion_status", "promotion_status"),
        Index("idx_memory_items_last_confirmed", "last_confirmed"),
    )


class MemoryPromotionLogModel(Base):
    """Audit log for memory promotion decisions"""
    
    __tablename__ = "memory_promotion_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    candidate_fact = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    confidence = Column(Float, nullable=False)
    consistency_score = Column(Float, nullable=True)
    promotion_status = Column(String, nullable=False)  # promoted, rejected, duplicate
    promotion_reason = Column(Text, nullable=True)
    source_conversation_id = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("UserModel", back_populates="promotion_logs")

    # Indexes
    __table_args__ = (
        Index("idx_promotion_log_user_status", "user_id", "promotion_status"),
        Index("idx_promotion_log_created_at", "created_at"),
    )


class MemoryFactExtractionModel(Base):
    """Track fact extraction from messages"""
    
    __tablename__ = "memory_fact_extraction"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    message_id = Column(String, nullable=False, index=True)
    conversation_id = Column(String, nullable=True, index=True)
    extracted_facts = Column(JSON, nullable=False)  # List of extracted facts
    classification_metadata = Column(JSON, nullable=True)
    extraction_confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("UserModel", back_populates="fact_extractions")

    # Indexes
    __table_args__ = (
        Index("idx_fact_extraction_user_message", "user_id", "message_id"),
        Index("idx_fact_extraction_conversation", "conversation_id"),
    )


class MemoryConsistencyModel(Base):
    """Track consistency checks between facts"""
    
    __tablename__ = "memory_consistency"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    fact_id = Column(String, nullable=False, index=True)
    compared_with_fact_id = Column(String, nullable=False, index=True)
    similarity_score = Column(Float, nullable=False)
    contradiction_detected = Column(String, nullable=True)  # Type of contradiction if any
    consistency_score = Column(Float, nullable=False)
    checked_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("UserModel", back_populates="consistency_checks")

    # Indexes
    __table_args__ = (
        Index("idx_consistency_user_fact", "user_id", "fact_id"),
        Index("idx_consistency_similarity", "similarity_score"),
    )


class MemoryUsageModel(Base):
    """Track memory usage and retrieval patterns"""
    
    __tablename__ = "memory_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    retrieved_facts_count = Column(Integer, nullable=False)
    retrieved_summaries_count = Column(Integer, nullable=False)
    total_retrieval_score = Column(Float, nullable=False)
    retrieval_timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSON, default=dict)

    # Relationships
    user = relationship("UserModel", back_populates="memory_usage")

    # Indexes
    __table_args__ = (
        Index("idx_memory_usage_user_timestamp", "user_id", "retrieval_timestamp"),
        Index("idx_memory_usage_score", "total_retrieval_score"),
    )


# Add relationships to existing UserModel
def add_memory_relationships():
    """Add memory relationships to existing UserModel"""
    
    from .models import UserModel

    UserModel.memory_items = relationship(
        "MemoryItemModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    UserModel.promotion_logs = relationship(
        "MemoryPromotionLogModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    UserModel.fact_extractions = relationship(
        "MemoryFactExtractionModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    UserModel.consistency_checks = relationship(
        "MemoryConsistencyModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    UserModel.memory_usage = relationship(
        "MemoryUsageModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )