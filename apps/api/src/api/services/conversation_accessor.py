"""Thin service-layer accessors for conversation persistence.

Routes must not import api.storage directly. This module gives route handlers
a stable, service-layer surface for the two conversation operations they need
without coupling them to the storage implementation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..storage.conversations import conversation_store as _store


async def get_conversation(conversation_id: str):
    return await _store.get_conversation(conversation_id)


async def add_message_to_conversation(
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    message_id: Optional[str] = None,
) -> bool:
    return await _store.add_message_to_conversation(
        conversation_id=conversation_id,
        role=role,
        content=content,
        metadata=metadata,
        message_id=message_id,
    )
