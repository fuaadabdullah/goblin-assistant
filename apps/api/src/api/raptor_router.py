import asyncio
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/raptor", tags=["raptor"])


class LogsRequest(BaseModel):
    max_chars: int = 1000


# Simple mock raptor state (in production, integrate with actual raptor system)
# RAPTOR settings moved to config/providers.toml ([default.raptor]) — the single source of truth
RAPTOR_STATE = {"running": False, "config_file": "config/providers.toml"}


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _detail_message(prefix: str, error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{prefix}: {message}"
    return f"{prefix}: Request failed"


@router.post("/start")
async def raptor_start():
    """Start raptor monitoring"""
    try:
        RAPTOR_STATE["running"] = True
        return {"running": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_detail_message("Failed to start raptor", e))


@router.post("/stop")
async def raptor_stop():
    """Stop raptor monitoring"""
    try:
        RAPTOR_STATE["running"] = False
        return {"running": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_detail_message("Failed to stop raptor", e))


@router.get("/status")
async def raptor_status():
    """Get raptor status"""
    try:
        return {
            "running": RAPTOR_STATE["running"],
            "config_file": RAPTOR_STATE["config_file"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=_detail_message("Failed to get raptor status", e)
        )


@router.post("/logs")
async def raptor_logs(request: LogsRequest):
    """Get raptor logs"""
    try:
        # Try to read from log file if it exists
        log_file = "logs/raptor.log"
        if os.path.exists(log_file):  # noqa: ASYNC240
            content = await asyncio.to_thread(_read_text_file, log_file)
            # Return last max_chars characters
            log_tail = (
                content[-request.max_chars :] if len(content) > request.max_chars else content
            )
        else:
            log_tail = "Log file not found. Raptor may not be configured."

        return {"log_tail": log_tail}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=_detail_message("Failed to read raptor logs", e)
        )


@router.get("/demo/{value}")
async def raptor_demo(value: str):
    """Demo endpoint for testing raptor"""
    try:
        if value.lower() == "boom":
            # Simulate an error for testing
            raise Exception("Demo error triggered")
        return {"result": f"Demo executed with value: {value}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_detail_message("Demo failed", e))
