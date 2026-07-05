"""
Storage abstractions for the Goblin Assistant API.

This module provides abstract interfaces and implementations for
various storage backends used by the API.
"""

from .api_keys import (
    APIKeyStore,
    DatabaseAPIKeyStore,
    FileAPIKeyStore,
    SecretManagerAPIKeyStore,
    create_api_key_store,
)
from .conversations import (
    Conversation,
    ConversationMessage,
    ConversationStore,
    ConversationStoreManager,
    conversation_store,
)
from .crypto import decrypt_secret, encrypt_secret
from .saas_service import SaaSSettingsService
from .tasks import (
    TaskStore,
    get_task_store,
    task_store,
)
from .usage_events import (
    UsageEventStore,
    get_usage_event_store,
    usage_event_store,
)

__all__ = [
    "APIKeyStore",
    "DatabaseAPIKeyStore",
    "FileAPIKeyStore",
    "SecretManagerAPIKeyStore",
    "create_api_key_store",
    "encrypt_secret",
    "decrypt_secret",
    "TaskStore",
    "task_store",
    "get_task_store",
    "ConversationStore",
    "ConversationStoreManager",
    "Conversation",
    "ConversationMessage",
    "conversation_store",
    "SaaSSettingsService",
    "UsageEventStore",
    "usage_event_store",
    "get_usage_event_store",
]
