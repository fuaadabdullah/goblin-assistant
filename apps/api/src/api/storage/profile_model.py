"""User profile model for structured user data"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from .models import Base


class UserProfileModel(Base):
    """Structured user profile aggregating goals, projects, and preferences from the entity graph."""

    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    goals = Column(JSON, default=list, nullable=False)  # List of goal strings
    projects = Column(JSON, default=dict, nullable=False)  # List of project names
    preferences = Column(JSON, default=dict, nullable=False)  # Dict of preference key-value pairs
    key_entities = Column(
        JSON, default=dict, nullable=False
    )  # Dict of entity_type -> list of entity objects
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, goals={len(self.goals)}, projects={len(self.projects)})>"
