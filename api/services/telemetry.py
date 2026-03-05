"""
Telemetry service with PII redaction for Goblin Assistant.

This module provides safe telemetry logging that:
- NEVER logs raw user messages
- Redacts PII before sending to Datadog
- Logs only aggregated metrics and hashes
- Tracks performance without exposing sensitive data

Usage:
    from api.services.telemetry import (
        log_inference_metrics,
        log_conversation_event,
        log_error_event
    )

    # Log inference metrics (safe for Datadog)
    log_inference_metrics(
        provider="groq",
        model="llama-3.1-70b",
        latency_ms=250,
        token_count=1500,
        cost_usd=0.0023,
        status_code=200
    )
"""

import os
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum

from .sanitization import mask_sensitive, hash_message_id, redact_for_logging

logger = logging.getLogger(__name__)

# Check if we're in production
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"
ENABLE_DATADOG = os.getenv("ENABLE_DATADOG", "false").lower() == "true"

# Try to import Datadog (optional dependency)
try:
    from datadog import initialize, statsd

    DATADOG_AVAILABLE = True

    if ENABLE_DATADOG:
        initialize(
            statsd_host=os.getenv("DATADOG_AGENT_HOST", "localhost"),
            statsd_port=int(os.getenv("DATADOG_AGENT_PORT", "8125")),
        )
        logger.info("Datadog telemetry initialized")
except ImportError:
    DATADOG_AVAILABLE = False
    logger.warning("Datadog not available - metrics will only log locally")


class EventType(str, Enum):
    """Telemetry event types."""

    CONVERSATION_START = "conversation.start"
    CONVERSATION_MESSAGE = "conversation.message"
    CONVERSATION_END = "conversation.end"
    INFERENCE_REQUEST = "inference.request"
    INFERENCE_SUCCESS = "inference.success"
    INFERENCE_ERROR = "inference.error"
    RAG_QUERY = "rag.query"
    RAG_INSERT = "rag.insert"
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    DATA_EXPORT = "data.export"
    DATA_DELETE = "data.delete"
    ERROR = "error"


def log_inference_metrics(
    provider: str,
    model: str,
    latency_ms: int,
    token_count: int,
    cost_usd: float,
    status_code: int,
    user_id: Optional[str] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Log inference metrics WITHOUT message content.

    Safe to send to Datadog - no PII included.

    Args:
        provider: LLM provider (groq, openai, anthropic, local)
        model: Model name
        latency_ms: Request latency in milliseconds
        token_count: Number of tokens used
        cost_usd: Cost in USD
        status_code: HTTP status code
        user_id: User ID (will be hashed)
        error: Error type if failed
        metadata: Additional safe metadata

    Example:
        >>> log_inference_metrics(
        ...     provider="groq",
        ...     model="llama-3.1-70b",
        ...     latency_ms=250,
        ...     token_count=1500,
        ...     cost_usd=0.0023,
        ...     status_code=200
        ... )
    """
    # Create tags for Datadog
    tags = [
        f"provider:{provider}",
        f"model:{model}",
        f"status:{status_code}",
    ]

    if error:
        tags.append(f"error_type:{error}")

    # Hash user_id for privacy
    if user_id:
        user_hash = hash_message_id(user_id)
        tags.append(f"user_hash:{user_hash[:8]}")

    # Send metrics to Datadog
    if DATADOG_AVAILABLE and ENABLE_DATADOG:
        try:
            statsd.histogram("goblin.inference.latency", latency_ms, tags=tags)
            statsd.increment("goblin.inference.requests", tags=tags)
            statsd.gauge("goblin.inference.tokens", token_count, tags=tags)
            statsd.gauge("goblin.inference.cost", cost_usd, tags=tags)

            if error:
                statsd.increment("goblin.inference.errors", tags=tags)
        except Exception as e:
            logger.error(f"Failed to send metrics to Datadog: {e}")

    # Local logging (safe)
    log_data = {
        "event": EventType.INFERENCE_SUCCESS
        if status_code == 200
        else EventType.INFERENCE_ERROR,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "token_count": token_count,
        "cost_usd": cost_usd,
        "status_code": status_code,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if error:
        log_data["error_type"] = error

    if metadata:
        log_data["metadata"] = mask_sensitive(metadata)

    logger.info(f"Inference: {log_data}")


def log_conversation_event(
    event_type: EventType,
    user_id: str,
    session_id: Optional[str] = None,
    message_count: Optional[int] = None,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Log conversation events with redaction.

    NEVER log raw message content.

    Args:
        event_type: Type of conversation event
        user_id: User ID (will be hashed)
        session_id: Session ID (will be hashed)
        message_count: Number of messages in conversation
        metadata: Additional safe metadata

    Example:
        >>> log_conversation_event(
        ...     event_type=EventType.CONVERSATION_START,
        ...     user_id="user_123",
        ...     session_id="session_xyz"
        ... )
    """
    # Hash identifiers for privacy
    user_hash = hash_message_id(user_id)
    session_hash = hash_message_id(session_id) if session_id else None

    # Create tags
    tags = [f"event_type:{event_type.value}", f"user_hash:{user_hash[:8]}"]

    if session_hash:
        tags.append(f"session_hash:{session_hash[:8]}")

    # Send to Datadog
    if DATADOG_AVAILABLE and ENABLE_DATADOG:
        try:
            statsd.increment(f"goblin.conversation.{event_type.value}", tags=tags)

            if message_count is not None:
                statsd.gauge(
                    "goblin.conversation.message_count", message_count, tags=tags
                )
        except Exception as e:
            logger.error(f"Failed to send conversation event to Datadog: {e}")

    # Local logging (safe)
    log_data = {
        "event": event_type.value,
        "user_hash": user_hash[:8],
        "session_hash": session_hash[:8] if session_hash else None,
        "message_count": message_count,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if metadata:
        log_data["metadata"] = mask_sensitive(metadata)

    logger.info(f"Conversation: {log_data}")


def log_rag_event(
    event_type: EventType,
    user_id: str,
    document_count: int,
    query_latency_ms: Optional[int] = None,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """
    Log RAG (Retrieval-Augmented Generation) events.

    Args:
        event_type: RAG_QUERY or RAG_INSERT
        user_id: User ID (will be hashed)
        document_count: Number of documents queried/inserted
        query_latency_ms: Query latency in milliseconds
        success: Whether operation succeeded
        error: Error message if failed
    """
    user_hash = hash_message_id(user_id)

    tags = [
        f"event_type:{event_type.value}",
        f"user_hash:{user_hash[:8]}",
        f"success:{success}",
    ]

    if error:
        tags.append(f"error_type:{error}")

    # Send to Datadog
    if DATADOG_AVAILABLE and ENABLE_DATADOG:
        try:
            statsd.increment(f"goblin.rag.{event_type.value}", tags=tags)
            statsd.gauge("goblin.rag.document_count", document_count, tags=tags)

            if query_latency_ms:
                statsd.histogram("goblin.rag.latency", query_latency_ms, tags=tags)
        except Exception as e:
            logger.error(f"Failed to send RAG event to Datadog: {e}")

    # Local logging
    logger.info(
        f"RAG: event={event_type.value}, docs={document_count}, success={success}"
    )


def log_privacy_event(
    event_type: EventType,
    user_id: str,
    action: str,
    item_count: Optional[int] = None,
    success: bool = True,
) -> None:
    """
    Log privacy-related events (export, delete).

    Args:
        event_type: DATA_EXPORT or DATA_DELETE
        user_id: User ID (will be hashed)
        action: Description of action
        item_count: Number of items affected
        success: Whether operation succeeded
    """
    user_hash = hash_message_id(user_id)

    tags = [f"event_type:{event_type.value}", f"action:{action}", f"success:{success}"]

    # Send to Datadog
    if DATADOG_AVAILABLE and ENABLE_DATADOG:
        try:
            statsd.increment(f"goblin.privacy.{event_type.value}", tags=tags)

            if item_count is not None:
                statsd.gauge("goblin.privacy.item_count", item_count, tags=tags)
        except Exception as e:
            logger.error(f"Failed to send privacy event to Datadog: {e}")

    # Local audit log (important for compliance)
    log_data = {
        "event": event_type.value,
        "user_hash": user_hash[:8],  # Hash for privacy
        "action": action,
        "item_count": item_count,
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
    }

    logger.info(f"Privacy: {log_data}")


def log_error_event(
    error_type: str,
    error_message: str,
    context: Optional[Dict] = None,
    severity: str = "error",
) -> None:
    """
    Log error events with redacted context.

    Args:
        error_type: Type/category of error
        error_message: Error message (will be sanitized)
        context: Additional context (will be masked)
        severity: error, warning, critical
    """
    tags = [f"error_type:{error_type}", f"severity:{severity}"]

    # Mask sensitive data in context
    safe_context = mask_sensitive(context) if context else {}

    # Send to Datadog
    if DATADOG_AVAILABLE and ENABLE_DATADOG:
        try:
            statsd.increment("goblin.error", tags=tags)
        except Exception as e:
            logger.error(f"Failed to send error event to Datadog: {e}")

    # Local logging
    log_data = {
        "event": EventType.ERROR.value,
        "error_type": error_type,
        "error_message": error_message[:200],  # Truncate
        "context": safe_context,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if severity == "critical":
        logger.critical(f"Error: {log_data}")
    elif severity == "warning":
        logger.warning(f"Error: {log_data}")
    else:
        logger.error(f"Error: {log_data}")


def log_message_safely(
    message: str, context: Optional[Dict] = None, max_preview_length: int = 50
) -> Dict[str, Any]:
    """
    Prepare message for safe logging.

    Returns redacted version suitable for telemetry.

    Args:
        message: Message text (will be redacted)
        context: Additional context (will be masked)
        max_preview_length: Max chars for preview

    Returns:
        Dictionary safe for logging
    """
    return redact_for_logging(message, context, max_preview_length)


# Export public API
__all__ = [
    "log_inference_metrics",
    "log_conversation_event",
    "log_rag_event",
    "log_privacy_event",
    "log_error_event",
    "log_message_safely",
    "EventType",
]
