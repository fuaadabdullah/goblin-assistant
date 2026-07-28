"""Shared fixtures for SSE error handling tests."""

from __future__ import annotations

import json

import pytest

from api.auth.router import User as AuthenticatedUser
from api.storage.conversations import Conversation


@pytest.fixture(name="authenticated_user")
def authenticated_user_fixture():
    return AuthenticatedUser(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
    )


@pytest.fixture(name="test_conversation")
def test_conversation_fixture():
    return Conversation(
        conversation_id="test-conv-id",
        user_id="test-user-id",
        title="Test Conversation",
        messages=[],
    )


def parse_sse_event(frame: str) -> dict:
    """Extract the JSON payload from an SSE frame.

    Accepts both single-line (`data: {...}`) and multi-line
    (`event: X\\ndata: {...}\\n\\n`) frames so tests are insensitive to
    whether the emitter sets an explicit event name.
    """
    for line in frame.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return {}


def _parsed_events(events):
    parsed = (parse_sse_event(item) for item in events)
    return [event for event in parsed if event]


def _error_events(events):
    return [event for event in _parsed_events(events) if event.get("code")]


def _content_events(events):
    return [event for event in _parsed_events(events) if "content" in event]
