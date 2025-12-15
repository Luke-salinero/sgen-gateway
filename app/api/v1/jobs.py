import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core import get_settings
from app.models import InternalJobRequest, JobCreateRequest, JobResultResponse
from app.services import ComputeAdapter, generate_job_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/sgen", tags=["jobs"])


def get_compute_adapter() -> ComputeAdapter:
    """Returns the Computer Adapter class, which operates between
    the API layer and the compute backend
    """

    return ComputeAdapter()


@router.post("/jobs", response_model=JobResultResponse, summary="Create S-Gen job")
async def create_job(
    request: JobCreateRequest,
    adapter: ComputeAdapter = Depends(get_compute_adapter),
):
    """
    Entry point for S-Gen jobs.

    In mock mode: returns a synthetic result immediately.
    In live mode: dispatches to the compute node and returns its response.
    """
    settings = get_settings()
    mode = settings.sgen_mode.lower()

    # TODO: integrate real auth & user identity; for now, a fixed placeholder
    user_id = "demo-user"

    job_id = generate_job_id()
    internal_job = InternalJobRequest(
        job_id=job_id,
        user_id=user_id,
        payload=request.payload,
        constraints={
            "timeout_seconds": settings.request_timeout_seconds,
        },
    )

    logger.info(
        "Received job request",
        extra={"job_id": job_id, "mode": mode},
    )

    if mode == "mock":
        internal_result = await adapter.run_job_mock(internal_job)
    elif mode == "live":
        internal_result = await adapter.run_job_live(internal_job)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid gateway mode: {mode!r}",
        )

    return JobResultResponse(
        job_id=internal_result.job_id,
        status=internal_result.status,
        mode=mode,
        result=internal_result.result,
        error=internal_result.error,
    )
