from __future__ import annotations

import asyncio
import base64
import json
import os
import secrets
from typing import Any
from urllib.parse import urlparse

import httpx
import oci
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(tags=["oracle-mcp"])

_SERVICE = "goblin-oracle-bridge"
_TAILSCALE_SOCKET = "/tmp/tailscaled.sock"
_TOOLS = [
    {
        "name": "oracle_status",
        "description": "Check the legacy Oracle A1 llama.cpp service through Goblin Assistant's Render tailnet path. Read-only.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "oci_control_status",
        "description": "Validate the restricted OCI control identity and report safe compute-control readiness. Read-only.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "oci_compute_inventory",
        "description": "List safe metadata for OCI compute instances visible to the restricted MCP identity. Read-only.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
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
        "oci_control_configured": all(
            bool(os.getenv(name, "").strip())
            for name in (
                "OCI_MCP_TENANCY",
                "OCI_MCP_USER",
                "OCI_MCP_FINGERPRINT",
                "OCI_MCP_REGION",
                "OCI_MCP_PRIVATE_KEY_B64",
            )
        ),
    }


def _oci_config() -> dict[str, str]:
    env_map = {
        "tenancy": "OCI_MCP_TENANCY",
        "user": "OCI_MCP_USER",
        "fingerprint": "OCI_MCP_FINGERPRINT",
        "region": "OCI_MCP_REGION",
    }
    values = {field: os.getenv(env_name, "").strip() for field, env_name in env_map.items()}
    private_key_b64 = os.getenv("OCI_MCP_PRIVATE_KEY_B64", "").strip()
    missing = [env_name for field, env_name in env_map.items() if not values[field]]
    if not private_key_b64:
        missing.append("OCI_MCP_PRIVATE_KEY_B64")
    if missing:
        raise RuntimeError("Missing OCI MCP configuration: " + ", ".join(missing))

    try:
        private_key = base64.b64decode(private_key_b64, validate=True).decode("utf-8")
    except Exception as exc:
        raise RuntimeError("OCI MCP private key is not valid base64 PEM") from exc

    # Oracle's optional OCI_API_KEY label is useful for local CLI files but is not
    # part of the PEM consumed through SDK key_content.
    if "\nOCI_API_KEY" in private_key:
        private_key = private_key.split("\nOCI_API_KEY", 1)[0].rstrip() + "\n"

    config = {
        **values,
        "key_content": private_key,
    }
    oci.config.validate_config(config)
    return config


def _safe_instances_sync(config: dict[str, str]) -> list[dict[str, Any]]:
    client = oci.core.ComputeClient(config)
    response = oci.pagination.list_call_get_all_results(
        client.list_instances,
        config["tenancy"],
    )
    return [
        {
            "name": instance.display_name,
            "state": instance.lifecycle_state,
            "shape": instance.shape,
            "availability_domain": instance.availability_domain,
            "time_created": instance.time_created.isoformat() if instance.time_created else None,
        }
        for instance in response.data
    ]


async def _oci_control_status() -> dict[str, Any]:
    try:
        config = _oci_config()
        instances = await asyncio.to_thread(_safe_instances_sync, config)
        return {
            "configured": True,
            "credentials_valid": True,
            "region": config["region"],
            "instance_count": len(instances),
            "write_scope": "restricted_by_oci_iam",
        }
    except Exception as exc:
        return {
            "configured": False,
            "credentials_valid": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


async def _oci_compute_inventory() -> dict[str, Any]:
    try:
        config = _oci_config()
        instances = await asyncio.to_thread(_safe_instances_sync, config)
        return {
            "region": config["region"],
            "count": len(instances),
            "instances": instances,
        }
    except Exception as exc:
        return {
            "count": 0,
            "instances": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


async def _run_tailscale(*args: str, timeout: float = 6.0) -> tuple[int | None, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "tailscale",
            f"--socket={_TAILSCALE_SOCKET}",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode,
            stdout.decode("utf-8", errors="replace").strip(),
            stderr.decode("utf-8", errors="replace").strip(),
        )
    except Exception as exc:
        return None, "", f"{type(exc).__name__}: {exc}"


async def _tailnet_diagnostics(endpoint: str) -> dict[str, Any]:
    host = urlparse(endpoint).hostname
    result: dict[str, Any] = {
        "target": host,
        "peer_found": False,
        "peer_online": None,
        "ping_ok": False,
    }
    if not host:
        result["error"] = "Endpoint host could not be parsed"
        return result

    code, stdout, stderr = await _run_tailscale("status", "--json")
    if code == 0:
        try:
            payload = json.loads(stdout)
            peers = payload.get("Peer", {})
            if isinstance(peers, dict):
                for peer in peers.values():
                    if not isinstance(peer, dict):
                        continue
                    ips = peer.get("TailscaleIPs") or []
                    if host in ips:
                        result["peer_found"] = True
                        result["peer_online"] = peer.get("Online")
                        result["peer_hostname"] = peer.get("HostName")
                        result["peer_active"] = peer.get("Active")
                        break
        except Exception as exc:
            result["status_error"] = f"{type(exc).__name__}: {exc}"
    else:
        result["status_error"] = stderr[-300:] or "tailscale status failed"

    ping_code, ping_stdout, ping_stderr = await _run_tailscale(
        "ping", "--c=1", "--timeout=5s", host, timeout=7.0
    )
    result["ping_ok"] = ping_code == 0
    if ping_stdout:
        result["ping"] = ping_stdout[-300:]
    elif ping_stderr:
        result["ping_error"] = ping_stderr[-300:]
    return result


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

    result["tailnet"] = await _tailnet_diagnostics(endpoint)

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
        tool_name = (params.get("name") or "").strip()
        if tool_name == "oracle_status":
            result = await _oracle_status()
        elif tool_name == "oci_control_status":
            result = await _oci_control_status()
        elif tool_name == "oci_compute_inventory":
            result = await _oci_compute_inventory()
        else:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": "Unknown tool"},
                },
                status_code=400,
            )
        return _rpc(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "structuredContent": result,
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
