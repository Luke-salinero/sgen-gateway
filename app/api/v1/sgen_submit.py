# app/api/v1/sgen_submit.py

import uuid

from fastapi import APIRouter, HTTPException

from app.core import get_settings
from app.models import (
    SGenErrorResponse,
    SGenSubmitRequest,
    SGenSubmitResponse,
)

router = APIRouter(prefix="", tags=["sgen"])


def mock_sgen_engine(req: SGenSubmitRequest) -> list[str]:
    """
    A deterministic but synthetic S-Gen mock engine.

    Generates valid bitstrings of length n, exactly k active bits.
    """
    n, k = req.n, req.k

    # For now: produce a single deterministic mock result.
    # Later: generate actual S-Gen patterns.
    bits = ["0"] * n
    for i in range(k):  # first k bits active
        bits[i] = "1"

    return [f"0b{''.join(bits)}"]


@router.post(
    "/submit",
    response_model=SGenSubmitResponse,
    responses={400: {"model": SGenErrorResponse}},
)
async def submit_job(req: SGenSubmitRequest):
    """Submits an SGen job to the compute node and returns an SGen response"""

    settings = get_settings()
    mode = settings.sgen_mode.lower()

    job_id = str(uuid.uuid4())

    if mode == "mock":
        results = mock_sgen_engine(req)
    else:
        # later: send to compute node
        raise HTTPException(status_code=500, detail="Live mode not implemented yet")

    return SGenSubmitResponse(
        status="ok",
        mode=mode,
        job_id=job_id,
        results=results,
        n=req.n,
        k=req.k,
    )
