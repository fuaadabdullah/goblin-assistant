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


async def require_operator(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Authorize a fleet management action: list, inspect, or evict.

    Authentication is not authorization. `get_current_user` proves somebody is
    logged in; it does not prove they operate this fleet. Goblin has no role
    model yet -- UserModel carries no admin or superuser column -- so in a
    multi-user deployment "any authenticated user" would mean any user could
    enumerate the fleet or evict node-001.

    Until roles exist, these routes sit behind a dedicated operator secret.
    When a real authorization dependency lands, replace this outright.
    """
    del request

    expected = node_settings.operator_secret
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "node management is not configured: set "
                "GOBLIN_NODE_OPERATOR_SECRET to use these routes"
            ),
        )

    # The registration secret is distributed to every node in the fleet. If it
    # also opened the management routes, compromising any single node would
    # hand over the ability to enumerate and evict all the others.
    if node_settings.registration_secret and hmac.compare_digest(
        expected, node_settings.registration_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "GOBLIN_NODE_OPERATOR_SECRET must differ from "
                "GOBLIN_NODE_REGISTRATION_SECRET"
            ),
        )

    presented = credentials.credentials if credentials else ""
    if not hmac.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="node management requires operator credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return presented
