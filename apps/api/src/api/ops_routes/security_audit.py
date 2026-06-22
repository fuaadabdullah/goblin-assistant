from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request

from ..ops.security import get_ops_audit_log, get_security_summary, require_ops_access

router = APIRouter()


def _detail_message(prefix: str, error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{prefix}: {message}"
    return f"{prefix}: Request failed"


@router.get("/security/status")
@require_ops_access("read")
async def get_security_status(request: Request) -> Dict[str, Any]:
    try:
        security_summary = get_security_summary()
        return {
            "success": True,
            "data": security_summary,
            "message": "Security status retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_detail_message("Failed to get security status", e),
        )


@router.get("/audit/log")
@require_ops_access("read")
async def get_audit_log(
    request: Request,
    limit: int = Query(100, description="Number of log entries to return"),
    offset: int = Query(0, description="Offset for pagination"),
) -> Dict[str, Any]:
    try:
        audit_log = await get_ops_audit_log(limit=limit, offset=offset)

        return {
            "success": True,
            "data": {
                "audit_log": audit_log,
                "total_entries": len(audit_log),
                "limit": limit,
                "offset": offset,
            },
            "message": "Audit log retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=_detail_message("Failed to get audit log", e))
