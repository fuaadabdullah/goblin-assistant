from __future__ import annotations

import asyncio
import os
import secrets
from urllib.parse import urlparse
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(tags=["oracle-mcp"])

_SERVICE = "goblin-oracle-bridge"
_TOOLS = [
    {
        "name": "oracle_status",
        "description": "Check the existing Oracle A1 llama.cpp service through Goblin Assistant's Render tailnet path. Read-only.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    }
]


def _authorized(authorization: str | None) -> None:
    token = os.getenv("ORACLE_MCP_BEARER_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Oracle MCP bearer token is not configured")
    expected = f"Bearer {token}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _rpc(request_id: Any, result: dict[str, Any]) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


@router.get("/mcp/oracle")
async def oracle_mcp_info() -> dict[str, Any]:
    return {
        "service": _SERVICE,
        "transport": "JSON-RPC over POST",
        "read_only": True,
        "oracle_endpoint_configured": bool(os.getenv("LLAMACPP_ORACLE_ENDPOINT", "").strip()),
        "oracle_api_key_configured": bool(os.getenv("LLAMACPP_ORACLE_API_KEY", "").strip()),
        "tailnet_auth_configured": bool(os.getenv("TAILSCALE_AUTHKEY", "").strip()),
    }


async def _tailnet_ping(endpoint: str) -> dict[str, Any]:
    host = urlparse(endpoint).hostname
    socket = "/tmp/tailscaled.sock"
    if not host or not os.path.exists(socket):
        return {"tailnet_peer_reachable": False, "tailnet_ping": "tailnet socket unavailable"}
    try:
        proc = await asyncio.create_subprocess_exec(
            "tailscale",
            f"--socket={socket}",
            "ping",
            "--c=1",
            "--timeout=5s",
            host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _stderr = await proc.communicate()
        detail = stdout.decode("utf-8", errors="replace").strip()[-500:]
        return {
            "tailnet_peer_reachable": proc.returncode == 0,
            "tailnet_ping": detail or f"tailscale ping exited {proc.returncode}",
        }
    except Exception as exc:
        return {
            "tailnet_peer_reachable": False,
            "tailnet_ping": f"{type(exc).__name__}: {exc}",
        }


async def _oracle_status() -> dict[str, Any]:
    endpoint = os.getenv("LLAMACPP_ORACLE_ENDPOINT", "").strip().rstrip("/")
    api_key = os.getenv("LLAMACPP_ORACLE_API_KEY", "").strip()
    proxy = os.getenv("LLAMACPP_ORACLE_PROXY", "").strip() or None
    result: dict[str, Any] = {
        "endpoint_configured": bool(endpoint),
        "api_key_configured": bool(api_key),
        "tailnet_auth_configured": bool(os.getenv("TAILSCALE_AUTHKEY", "").strip()),
        "reachable": False,
    }
    if not endpoint:
        result["error"] = "LLAMACPP_ORACLE_ENDPOINT is not configured"
        return result

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=8.0, proxy=proxy) as client:
            response = await client.get(f"{endpoint}/v1/models", headers=headers)
        result["http_status"] = response.status_code
        if response.status_code == 200:
            payload = response.json()
            result["reachable"] = True
            result["models"] = [
                str(item.get("id"))
                for item in payload.get("data", [])
                if isinstance(item, dict) and item.get("id")
            ][:20]
        else:
            result["error"] = "Oracle llama.cpp endpoint returned a non-200 response"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result.update(await _tailnet_ping(endpoint))
    return result


@router.post("/mcp/oracle")
async def oracle_mcp(
    request: dict[str, Any],
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    _authorized(authorization)
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if method == "initialize":
        return _rpc(
            request_id,
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": _SERVICE, "version": "0.1.0"},
            },
        )
    if method in {"notifications/initialized", "ping"}:
        return _rpc(request_id, {})
    if method == "tools/list":
        return _rpc(request_id, {"tools": _TOOLS})
    if method == "tools/call":
        if (params.get("name") or "").strip() != "oracle_status":
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": "Unknown tool"},
                },
                status_code=400,
            )
        status = await _oracle_status()
        return _rpc(
            request_id,
            {
                "content": [{"type": "text", "text": __import__("json").dumps(status)}],
                "structuredContent": status,
            },
        )

    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        },
        status_code=404,
    )
