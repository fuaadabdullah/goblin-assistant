"""Goblin Assistant Services Package - Privacy & Security Services Only."""

import importlib.util
import os

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

_VECTOR_STORE_DEFAULT = (
    "false"
    if os.getenv("ENVIRONMENT", "development").lower() == "production"
    else "true"
)
VECTOR_STORE_AVAILABLE = (
    os.getenv("ENABLE_VECTOR_STORE", _VECTOR_STORE_DEFAULT).strip().lower()
    in {"1", "true", "yes", "on"}
    and importlib.util.find_spec("chromadb") is not None
)


def __getattr__(name: str):
    if name == "SafeVectorStore":
        if not VECTOR_STORE_AVAILABLE:
            return None

        from .safe_vector_store import SafeVectorStore as _SafeVectorStore

        return _SafeVectorStore

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
