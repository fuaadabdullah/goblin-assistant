"""
MCP (Model Control Plane) database models and schema.

This module defines the database schema for the MCP service including
request tracking, event logging, and result storage.
"""

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime
import uuid

Base = declarative_base()


class MCPRequest(Base):
    """MCP request tracking table."""

    __tablename__ = "mcp_request"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_hash = Column(String(16), nullable=False, index=True)  # Truncated SHA256 hash
    status = Column(
        String(20), nullable=False, index=True
    )  # pending/running/finished/failed/cancelled
    task_type = Column(String(50))  # code/chat/transform/workflow
    priority = Column(Integer, default=50)
    provider_hint = Column(String(100))  # e.g., "local_ollama" or "openai"
    cost_estimate_usd = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_provider = Column(String(100))
    attempts = Column(Integer, default=0)
    trace_id = Column(String(32))  # For APM tracing


class MCPEvent(Base):
    """MCP event logging table for audit and debugging."""

    __tablename__ = "mcp_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), nullable=False, index=True)
    ts = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String(50), index=True)  # log, trace, provider_call, fallback
    payload = Column(Text)  # JSON as text for SQLite


class MCPResult(Base):
    """MCP result storage table."""

    __tablename__ = "mcp_result"

    request_id = Column(String(36), primary_key=True)
    result = Column(Text)  # JSON as text for SQLite
    tokens = Column(Integer)
    cost_usd = Column(Float)
    finished_at = Column(DateTime, default=datetime.utcnow)


def get_database_url():
    """Get database URL from environment variables."""
    return os.getenv("DATABASE_URL", "sqlite:///./mcp_test.db")


def create_engine_and_session():
    """Create SQLAlchemy engine and session factory."""
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def init_database():
    """Initialize database tables."""
    engine, _ = create_engine_and_session()
    Base.metadata.create_all(bind=engine)
    print("MCP database tables created successfully")


if __name__ == "__main__":
    init_database()
