"""Goblin Assistant Services Package - Privacy & Security Services Only."""

# Privacy & Security Services
from .sanitization import (
    sanitize_input_for_model,
    is_sensitive_content,
    mask_sensitive,
    hash_message_id,
    PII_PATTERNS,
    SENSITIVE_KEYWORDS,
)

from .telemetry import (
    log_inference_metrics,
    log_conversation_event,
)

try:
    from .safe_vector_store import SafeVectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    # sentence-transformers not installed, vector store unavailable
    VECTOR_STORE_AVAILABLE = False
    SafeVectorStore = None

__all__ = [
    # Privacy & Security
    "sanitize_input_for_model",
    "is_sensitive_content",
    "mask_sensitive",
    "hash_message_id",
    "PII_PATTERNS",
    "SENSITIVE_KEYWORDS",
    "log_inference_metrics",
    "log_conversation_event",
    "SafeVectorStore",
    "VECTOR_STORE_AVAILABLE",
]
