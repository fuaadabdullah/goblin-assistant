"""HTTP surface for the node registry.

Two distinct credentials, because the callers are not the same kind of thing.
Nodes publish heartbeats with the registration secret, which is distributed
across the fleet. Operators list, inspect and evict with a separate operator
secret, which is not -- so compromising a node does not hand over the fleet.
"""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_node_secret, require_operator
from .endpoint_policy import InvalidEndpoint, validate_endpoint
from .models import NodeHeartbeat, NodeView
from .registry import node_registry

router = APIRouter(prefix="/nodes", tags=["nodes"])


# Management routes are AUTHORIZED, not merely authenticated. Goblin has no
# role model, so a logged-in user is not evidence of being an operator: with
# only get_current_user here, any user of a multi-user deployment could
# enumerate the fleet or evict node-001. See auth.require_operator.
_OPERATOR_AUTH = [Depends(require_operator)]


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
