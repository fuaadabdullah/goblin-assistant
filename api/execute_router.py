from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import asyncio

router = APIRouter(prefix="/execute", tags=["execute"])


class ExecuteRequest(BaseModel):
    goblin: str
    task: str
    code: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class ExecuteResponse(BaseModel):
    taskId: str
    status: str = "queued"


# Simple in-memory task storage
TASKS = {}


@router.post("/", response_model=ExecuteResponse)
async def execute_task(request: ExecuteRequest):
    """Execute a task using the specified goblin"""
    try:
        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Store task information
        TASKS[task_id] = {
            "goblin": request.goblin,
            "task": request.task,
            "code": request.code,
            "provider": request.provider,
            "model": request.model,
            "status": "running",
            "created_at": asyncio.get_event_loop().time(),
        }

        # For now, simulate task execution
        # In a real implementation, this would queue the task for the goblin
        asyncio.create_task(simulate_task_execution(task_id))

        return ExecuteResponse(taskId=task_id, status="queued")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


async def simulate_task_execution(task_id: str):
    """Simulate task execution (replace with actual goblin execution logic)"""
    await asyncio.sleep(2)  # Simulate processing time

    # Mark task as completed
    if task_id in TASKS:
        TASKS[task_id]["status"] = "completed"
        TASKS[task_id]["result"] = (
            f"Task executed by {TASKS[task_id]['goblin']}: {TASKS[task_id]['task']}"
        )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a task"""
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")

    task = TASKS[task_id]
    return {
        "taskId": task_id,
        "status": task["status"],
        "result": task.get("result"),
        "goblin": task["goblin"],
        "task": task["task"],
    }
