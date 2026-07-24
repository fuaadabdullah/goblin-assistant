"""Formatting And Auth SSE tests."""

from unittest.mock import patch

from fastapi import HTTPException

from api.chat_router import generate_chat_stream
from api.chat_router.streaming import _format_unhandled_stream_error

from .conftest import _error_events


def test_unhandled_stream_error_formatter_preserves_message():
    assert _format_unhandled_stream_error(RuntimeError("boom")) == "boom"
    assert _format_unhandled_stream_error(RuntimeError("")) == (
        "An unexpected error occurred. Your message was saved if it got this far."
    )


async def test_auth_failure_returns_error_event(authenticated_user):
    with patch(
        "api.chat_router._require_owned_conversation",
        side_effect=HTTPException(status_code=401, detail="Unauthorized"),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="wrong-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    error_events = _error_events(events)

    assert error_events
    assert any(event.get("code") == "auth-failed" for event in error_events)
    assert all(event.get("is_recoverable") is False for event in error_events)
