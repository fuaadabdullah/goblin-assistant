"""
SQLAlchemy models for feedback loop persistence.

Tracks explicit user signals (thumbs up/down) and implicit behavioral signals
(regenerate, delete, continue, provider switch) to close the learning loop.

See docs/architecture/FEEDBACK_LOOPS.md for architecture and design.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    true,
)
from sqlalchemy.orm import relationship

from .models import Base


class FeedbackEventModel(Base):
    """Persistent record of every explicit and implicit feedback signal."""

    __tablename__ = "feedback_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(String, nullable=False, index=True)
    message_id = Column(String, nullable=False, index=True)
    request_id = Column(String, nullable=True, index=True)  # correlation to routing_events

    # The feedback signal type
    signal = Column(
        String, nullable=False, index=True
    )  # 'thumbs_up', 'thumbs_down', 'regenerate', 'delete', 'continue', 'provider_switch', 'model_switch', 'copy'
    rating = Column(Integer, nullable=True)  # +1 or -1 (for thumbs up/down)

    # Context at time of signal
    department = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    task_type = Column(String, nullable=True)
    intent_label = Column(String, nullable=True)
    complexity_score = Column(Float, nullable=True)

    # Previous context (for switches/comparisons)
    previous_provider = Column(String, nullable=True)
    previous_model = Column(String, nullable=True)

    # Learning application tracking
    weight = Column(Float, nullable=False, default=1.0)
    applied_to_bandit = Column(Boolean, nullable=False, default=False, server_default=true())
    applied_to_router = Column(Boolean, nullable=False, default=False, server_default=true())
    applied_to_profile = Column(Boolean, nullable=False, default=False, server_default=true())

    # Metadata
    metadata_ = Column("metadata", String, nullable=True)  # JSON string

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("UserModel", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_feedback_events_user_created", "user_id", "created_at"),
        Index("idx_feedback_events_signal_created", "signal", "created_at"),
        Index("idx_feedback_events_dept_created", "department", "created_at"),
        Index("idx_feedback_events_provider_created", "provider", "created_at"),
    )


class MessageOutcomeModel(Base):
    """Per-message behavioral outcome tracking.

    Records what happened after each assistant message was delivered:
    was it regenerated? deleted? copied? Did the user continue the conversation?
    Did they switch provider/model before the next message?
    """

    __tablename__ = "message_outcomes"

    outcome_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, ForeignKey("messages.message_id"), nullable=False, index=True)
    conversation_id = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Outcome flags (observed behavior)
    was_regenerated = Column(Boolean, nullable=False, default=False)
    was_deleted = Column(Boolean, nullable=False, default=False)
    was_copied = Column(Boolean, nullable=False, default=False)
    conversation_continued = Column(Boolean, nullable=False, default=False)
    provider_switched_before_next = Column(Boolean, nullable=False, default=False)
    model_switched_before_next = Column(Boolean, nullable=False, default=False)

    # Correlation
    next_message_id = Column(String, nullable=True)  # if continued, what was the next message
    previous_provider = Column(String, nullable=True)
    previous_model = Column(String, nullable=True)
    new_provider = Column(String, nullable=True)  # if switched
    new_model = Column(String, nullable=True)  # if switched

    # Composite quality score accumulated from all signals for this message.
    # Incremented/decremented by outcome_scorer.points_for(signal) on each event.
    quality_score = Column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    user = relationship("UserModel", foreign_keys=[user_id])
    message = relationship("MessageModel", foreign_keys=[message_id])

    __table_args__ = (
        Index("idx_message_outcomes_message", "message_id"),
        Index("idx_message_outcomes_conversation", "conversation_id", "created_at"),
    )
