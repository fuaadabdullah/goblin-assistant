"""HTTP surface for the node registry.

Every route here is authenticated. The heartbeat uses a node registration
secret; the inspect/evict routes use the normal authenticated-user dependency,
because those are operator actions rather than machine ones.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_node_secret
from .endpoint_policy import InvalidEndpoint, validate_endpoint
from .models import NodeHeartbeat, NodeView
from .registry import node_registry

router = APIRouter(prefix="/nodes", tags=["nodes"])


# The inspect/evict routes are operator actions, so they reuse the app's
# normal authenticated-user dependency. The import is guarded only so this
# module stays importable in isolation (unit tests mount the router without
# the database session machinery); in the running app it is always present.
try:  # pragma: no cover - exercised implicitly by the app
    from ..auth.router.dependencies import get_current_user as _get_current_user
except Exception:  # noqa: BLE001
    _get_current_user = None

if _get_current_user is None:  # pragma: no cover

    async def _deny() -> Any:
        # Fail closed: never expose the registry just because auth failed to
        # import.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication unavailable",
        )

    _OPERATOR_AUTH = [Depends(_deny)]
else:
    _OPERATOR_AUTH = [Depends(_get_current_user)]


@router.post("/heartbeat", dependencies=[Depends(require_node_secret)])
async def heartbeat(payload: NodeHeartbeat) -> Dict[str, object]:
    """Accept a node's periodic self-announcement.

    Upserts by node_id: the first heartbeat registers the node, subsequent
    ones refresh it. There is no separate registration call, so a node that
    restarts or changes its model set needs no operator intervention.

    The advertised endpoint is validated before it is stored, because dispatch
    will later send real user prompts to it.
    """
    if payload.endpoint:
        try:
            payload.endpoint = validate_endpoint(payload.endpoint)
        except InvalidEndpoint as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="rejected endpoint: {}".format(exc),
            ) from exc

    record = node_registry.upsert(payload)
    return {
        "ok": True,
        "node_id": record.node_id,
        "registered": record.heartbeat_count == 1,
        "ttl_seconds": node_registry.ttl_seconds,
    }


@router.get("", response_model=List[NodeView], dependencies=_OPERATOR_AUTH)
async def list_nodes() -> List[NodeView]:
    """All known nodes with their effective (staleness-aware) status."""
    return [node_registry.view(record) for record in node_registry.all()]


@router.get("/{node_id}", response_model=NodeView, dependencies=_OPERATOR_AUTH)
async def get_node(node_id: str) -> NodeView:
    record = node_registry.get(node_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown node: {}".format(node_id))
    return node_registry.view(record)


@router.delete("/{node_id}", dependencies=_OPERATOR_AUTH)
async def forget_node(node_id: str) -> Dict[str, object]:
    """Drop a node immediately rather than waiting for its heartbeat to lapse."""
    if not node_registry.forget(node_id):
        raise HTTPException(status_code=404, detail="unknown node: {}".format(node_id))
    return {"ok": True, "node_id": node_id, "forgotten": True}
