from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobCreatedResponse(BaseModel):
    """Information pertaining to the initial creation of an SGen Job"""

    job_id: str
    status: str = Field(..., description="queued, mocked, running, etc.")
    mode: str = Field(..., description="mock or live")


class JobResultResponse(BaseModel):
    """Information pertaining to the result of an SGen job"""

    job_id: str
    status: str
    mode: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
