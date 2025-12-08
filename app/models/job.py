from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JobRequestPayload(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    resolution: str = Field("1024x1024", pattern=r"^\d+x\d+$")
    steps: int = Field(50, ge=1, le=100)
    seed: Optional[int] = None


class JobCreateRequest(BaseModel):
    # Public API envelope for creating a job
    payload: JobRequestPayload


class JobStatus(str):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MOCKED = "mocked"


class InternalJobRequest(BaseModel):
    # What we send to the compute node
    job_id: str
    user_id: str
    payload: JobRequestPayload
    constraints: Dict[str, Any] = Field(default_factory=dict)


class InternalJobResult(BaseModel):
    job_id: str
    status: str
    result: Dict[str, Any] | None = None
    error: Dict[str, Any] | None = None
