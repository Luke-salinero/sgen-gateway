from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str = Field(..., description="queued, mocked, running, etc.")
    mode: str = Field(..., description="mock or live")


class JobResultResponse(BaseModel):
    job_id: str
    status: str
    mode: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
