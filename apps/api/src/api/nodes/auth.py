"""Authentication for the node control plane.

Nodes are not users: they have no session, no database row, and no business
holding a user credential. They authenticate with a dedicated registration
secret instead, which keeps the heartbeat path free of a DB round trip on
every beat from every node.

The read/delete endpoints are a different matter -- those are operator
actions, and they reuse the normal authenticated-user dependency.
"""

from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import node_settings

_bearer = HTTPBearer(auto_error=False)


async def require_node_secret(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Authenticate a node publishing a heartbeat.

    Fails CLOSED when no secret is configured. An unauthenticated node
    control plane would let anyone register a node, mark it online, and
    point its endpoint at a host they control -- at which point real user
    prompts get delivered to them. Refusing to run is the correct behaviour,
    not an inconvenience to be defaulted away.
    """
    del request  # kept for symmetry with other dependencies in this codebase

    expected = node_settings.registration_secret
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "node registration is not configured: set "
                "GOBLIN_NODE_REGISTRATION_SECRET before nodes can register"
            ),
        )

    presented = credentials.credentials if credentials else ""
    # Constant time: a naive == leaks the secret one byte at a time to anyone
    # willing to measure.
    if not hmac.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid node registration credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return presented
