"""
Sandbox job data helpers — decode Redis payloads, build model objects, file I/O,
and emit completion events.
"""

import asyncio
from typing import Optional

import structlog

from .core.contracts import SandboxExecutionCompletedPayload
from .observability.events import event_emitter
from .sandbox_models import JobStatus, SandboxJobSummary

logger = structlog.get_logger()


def _decode_job_data(job_data: dict[bytes, bytes]) -> dict[str, str]:
    return {k.decode("utf-8"): v.decode("utf-8") for k, v in job_data.items()}


def _parse_exit_code(job_info: dict[str, str]) -> Optional[int]:
    if not job_info.get("exit_code"):
        return None
    return int(job_info["exit_code"])


def _job_status(job_id: str, job_info: dict[str, str]) -> JobStatus:
    return JobStatus(
        job_id=job_id,
        status=job_info.get("status", "unknown"),
        created_at=job_info.get("created_at", ""),
        started_at=job_info.get("started_at"),
        finished_at=job_info.get("finished_at"),
        exit_code=_parse_exit_code(job_info),
        error=job_info.get("error"),
    )


def _job_summary(job_info: dict[str, str]) -> SandboxJobSummary:
    return SandboxJobSummary(
        job_id=job_info.get("job_id", ""),
        status=job_info.get("status", "unknown"),
        language=job_info.get("language", ""),
        created_at=job_info.get("created_at", ""),
        started_at=job_info.get("started_at"),
        finished_at=job_info.get("finished_at"),
        exit_code=_parse_exit_code(job_info),
        error=job_info.get("error"),
    )


async def _run_blocking(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


def _write_text_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


async def _emit_sandbox_completed(job_id: str, job_info: dict[str, str]) -> None:
    if job_info.get("status") not in {"finished", "failed", "cancelled"}:
        return
    await event_emitter.emit(
        "sandbox.execution.completed",
        source="api.sandbox_api",
        payload=SandboxExecutionCompletedPayload(
            job_id=job_id,
            status=job_info.get("status", "unknown"),
            language=job_info.get("language"),
            exit_code=_parse_exit_code(job_info),
            started_at=job_info.get("started_at"),
            finished_at=job_info.get("finished_at"),
            error=job_info.get("error"),
        ),
    )
