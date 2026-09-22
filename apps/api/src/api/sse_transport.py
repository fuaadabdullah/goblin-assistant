"""Shared Server-Sent Events transport.

Keeps the existing preformatted SSE frames intact while delegating connection
lifecycle, keepalive pings, disconnect detection, and send timeouts to
sse-starlette.
"""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Mapping
from typing import Union

from sse_starlette import EventSourceResponse

SSEFrame = Union[str, bytes]


async def _encoded_frames(content: AsyncIterable[SSEFrame]) -> AsyncIterator[bytes]:
    async for frame in content:
        if isinstance(frame, bytes):
            yield frame
        else:
            yield frame.encode("utf-8")


def event_source_response(
    content: AsyncIterable[SSEFrame],
    *,
    headers: Mapping[str, str] | None = None,
    ping: int = 15,
    send_timeout: float = 30.0,
) -> EventSourceResponse:
    """Return a production SSE response without rewriting existing frames."""

    response_headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    if headers:
        response_headers.update(headers)

    # Do not set a Connection header here. ASGI/server protocol negotiation
    # owns that detail, and HTTP/2 forbids connection-specific headers.
    response_headers.pop("Connection", None)

    return EventSourceResponse(
        _encoded_frames(content),
        headers=response_headers,
        ping=ping,
        send_timeout=send_timeout,
    )
