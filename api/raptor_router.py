from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter(prefix="/raptor", tags=["raptor"])


class LogsRequest(BaseModel):
    max_chars: int = 1000


# Simple mock raptor state (in production, integrate with actual raptor system)
RAPTOR_STATE = {"running": False, "config_file": "config/raptor.ini"}


@router.post("/start")
async def raptor_start():
    """Start raptor monitoring"""
    try:
        RAPTOR_STATE["running"] = True
        return {"running": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start raptor: {str(e)}")


@router.post("/stop")
async def raptor_stop():
    """Stop raptor monitoring"""
    try:
        RAPTOR_STATE["running"] = False
        return {"running": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop raptor: {str(e)}")


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
            status_code=500, detail=f"Failed to get raptor status: {str(e)}"
        )


@router.post("/logs")
async def raptor_logs(request: LogsRequest):
    """Get raptor logs"""
    try:
        # Try to read from log file if it exists
        log_file = "logs/raptor.log"
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                content = f.read()
                # Return last max_chars characters
                log_tail = (
                    content[-request.max_chars :]
                    if len(content) > request.max_chars
                    else content
                )
        else:
            log_tail = "Log file not found. Raptor may not be configured."

        return {"log_tail": log_tail}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read raptor logs: {str(e)}"
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
        raise HTTPException(status_code=500, detail=f"Demo failed: {str(e)}")
