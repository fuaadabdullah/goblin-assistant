"""HTTP surface for the node registry."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from .models import NodeHeartbeat, NodeView
from .registry import node_registry

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("/heartbeat")
async def heartbeat(payload: NodeHeartbeat) -> Dict[str, object]:
    """Accept a node's periodic self-announcement.

    Upserts by node_id: the first heartbeat registers the node, subsequent
    ones refresh it. There is no separate registration call, so a node that
    restarts or changes its model set needs no operator intervention.
    """
    record = node_registry.upsert(payload)
    return {
        "ok": True,
        "node_id": record.node_id,
        "registered": record.heartbeat_count == 1,
        "ttl_seconds": node_registry.ttl_seconds,
    }


@router.get("", response_model=List[NodeView])
async def list_nodes() -> List[NodeView]:
    """All known nodes with their effective (staleness-aware) status."""
    return [node_registry.view(record) for record in node_registry.all()]


@router.get("/{node_id}", response_model=NodeView)
async def get_node(node_id: str) -> NodeView:
    record = node_registry.get(node_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown node: {}".format(node_id))
    return node_registry.view(record)


@router.delete("/{node_id}")
async def forget_node(node_id: str) -> Dict[str, object]:
    """Drop a node immediately rather than waiting for its heartbeat to lapse."""
    if not node_registry.forget(node_id):
        raise HTTPException(status_code=404, detail="unknown node: {}".format(node_id))
    return {"ok": True, "node_id": node_id, "forgotten": True}
