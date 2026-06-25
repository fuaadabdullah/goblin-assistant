"""Pure utility helpers for the chat router.

These functions perform no I/O of their own (other than reading from the
conversation store, in the ownership helpers). They're imported by the
route submodules and re-exported from `api.chat_router` for tests.
"""

import json
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.router import User as AuthenticatedUser
from ..providers.base import ProviderErrorCategory
from ..storage.conversations import Conversation
from . import _runtime as _cr


def _format_sse_event(event: str, payload: Dict[str, Any]) -> str:
    """Format a compliant SSE event frame with explicit event/data fields."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _latest_snippet(conversation: Conversation) -> Optional[str]:
    if not conversation.messages:
        return None

    latest = conversation.messages[-1].content.strip()
    if not latest:
        return None

    if len(latest) <= 160:
        return latest
    return f"{latest[:157].rstrip()}..."


async def _require_owned_conversation(
    conversation_id: str, current_user: AuthenticatedUser
) -> Conversation:
    conversation = await _cr.conversation_store.get_conversation(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


async def _assert_conversation_owned(
    conversation_id: str,
    current_user: AuthenticatedUser,
    db: AsyncSession,
) -> None:
    """Lightweight ownership check — no message loading. Raises 404 if not owned."""
    if not await _cr.conversation_store.check_conversation_owner(
        conversation_id, current_user.id, db=db
    ):
        raise HTTPException(status_code=404, detail="Conversation not found")


def _extract_usage_and_cost(
    provider_response: Any,
) -> tuple[Optional[Dict[str, Any]], Optional[float], Optional[str]]:
    if not isinstance(provider_response, dict):
        return None, None, None

    result_data = provider_response.get("result")
    raw = result_data.get("raw") if isinstance(result_data, dict) else None
    if not isinstance(raw, dict):
        return None, None, None

    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else None

    cost_value = raw.get("cost_usd", raw.get("cost"))
    cost_usd = float(cost_value) if isinstance(cost_value, (int, float)) else None

    correlation_value = raw.get("correlation_id")
    correlation_id = correlation_value if isinstance(correlation_value, str) else None

    return usage, cost_usd, correlation_id


def _raise_structured_provider_error(provider_response: Dict[str, Any]) -> None:
    category_raw = provider_response.get("error_category")
    category = str(category_raw or ProviderErrorCategory.UNKNOWN.value)

    if category == ProviderErrorCategory.AUTH.value:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "category": category,
                "message": "Authentication failed. Please check your credentials.",
            },
        )

    if category == ProviderErrorCategory.RATE_LIMIT.value:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "CHAT_RATE_LIMITED",
                "category": category,
                "message": "Request rate limit exceeded. Please retry shortly.",
                "retry_after": 2,
            },
        )

    if category == ProviderErrorCategory.TIMEOUT.value:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "CHAT_TIMEOUT",
                "category": category,
                "message": "The request took too long to process.",
            },
        )

    if category == ProviderErrorCategory.MODEL_ERROR.value:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CHAT_PROCESSING_UNAVAILABLE",
                "category": category,
                "message": "Unable to process this request with the current configuration.",
            },
        )

    if category in {
        ProviderErrorCategory.SERVER_ERROR.value,
        ProviderErrorCategory.CONNECTION.value,
    }:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_BACKEND_UNAVAILABLE",
                "category": category,
                "message": "The processing service is temporarily unavailable. Please retry in a moment.",
            },
        )

    raise HTTPException(
        status_code=502,
        detail={
            "code": "CHAT_PROCESSING_ERROR",
            "category": category,
            "message": "An unexpected processing error occurred.",
        },
    )
