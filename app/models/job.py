from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobRequestPayload(BaseModel):
    """Information pertaining to the initial prompt and request for SGen"""

    prompt: str = Field(..., min_length=1, max_length=4000)
    resolution: str = Field("1024x1024", pattern=r"^\d+x\d+$")
    steps: int = Field(50, ge=1, le=100)
    seed: Optional[int] = None


class JobCreateRequest(BaseModel):
    """Public API envelope for creating a job"""

    # Public API envelope for creating a job
    payload: JobRequestPayload


class JobStatus(str):
    """Information pertaining to the current status of an SGen Job"""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MOCKED = "mocked"


class InternalJobRequest(BaseModel):
    """Information that SGen sends the compute node"""

    # What we send to the compute node
    job_id: str
    user_id: str
    payload: JobRequestPayload
    constraints: Dict[str, Any] = Field(default_factory=dict)


class InternalJobResult(BaseModel):
    """Information that we receive from the compute node"""

    job_id: str
    status: str
    result: Dict[str, Any] | None = None
    error: Dict[str, Any] | None = None
