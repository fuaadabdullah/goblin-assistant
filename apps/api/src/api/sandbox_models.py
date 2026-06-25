"""
Pydantic models and exceptions for the Sandbox API.

Extracted from sandbox_api.py to keep the route module focused on
request handling. Import these from sandbox_api if you need backward
compatibility, or directly from here for new code.
"""

from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class SandboxExecutionError(Exception):
    """Raised when a sandbox job cannot be queued or executed."""

    def __init__(self, job_id: str, container_id: str | None, reason: str):
        self.job_id = job_id
        self.container_id = container_id
        self.reason = reason
        super().__init__(f"Sandbox execution failed [{job_id}]: {reason}")


class SubmitJobRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    language: str
    source: str = Field(
        validation_alias=AliasChoices("source", "code", "task"),
    )
    timeout: Optional[int] = 10
    runtime_args: Optional[str] = ""


class JobStatus(BaseModel):
    job_id: str
    status: str  # queued, running, finished, failed, cancelled
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


class ArtifactInfo(BaseModel):
    name: str
    size: int
    url: str
    created_at: str


class SubmitJobResponse(BaseModel):
    job_id: str


class JobLogsResponse(BaseModel):
    logs: str


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactInfo]


class CancelJobResponse(BaseModel):
    message: str


class SandboxHealthResponse(BaseModel):
    status: str
    redis_connected: bool
    image_configured: bool
    queue_depth: int
    enabled: bool
    message: Optional[str] = None
    redis_error: Optional[str] = None


class SandboxJobSummary(BaseModel):
    job_id: str
    status: str
    language: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


class SandboxJobsResponse(BaseModel):
    jobs: list[SandboxJobSummary]
    total: int
