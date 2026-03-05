"""
Universal Secrets Adapter for Goblin Assistant

This module provides a unified interface for secrets management across
Bitwarden and HashiCorp Vault, enabling consistent secrets operations
in the goblin-assistant backend.
"""

from .base import (
    SecretAdapter,
    SecretAdapterError,
    SecretNotFoundError,
    SecretUnauthorizedError,
    SecretBackendError,
    SecretValidationError,
)
from .factory import create_adapter

__all__ = [
    "SecretAdapter",
    "SecretAdapterError",
    "SecretNotFoundError",
    "SecretUnauthorizedError",
    "SecretBackendError",
    "SecretValidationError",
    "create_adapter",
]

__version__ = "1.0.0"
