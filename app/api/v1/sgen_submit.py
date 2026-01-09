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

# simple in-memory job store (mock-only)
JOB_STORE: dict[str, dict] = {}


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
    settings = get_settings()
    mode = settings.sgen_mode.lower()

    job_id = str(uuid.uuid4())

    if mode == "mock":
        results = mock_sgen_engine(req)
        status = "mocked"
        result_payload = {
            "results": results,
            "n": req.n,
            "k": req.k,
        }
    else:
        raise HTTPException(status_code=500, detail="Live mode not implemented yet")

    job = {
        "job_id": job_id,
        "status": status,
        "mode": mode,
        "result": result_payload,
        "error": None,
    }

    JOB_STORE[job_id] = job
    return job


@router.get(
    "/get_job_status/{job_id}",
    response_model=SGenSubmitResponse,
)
async def get_job_status(job_id: str):
    """Fetch status/result for an existing SGen job."""

    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
