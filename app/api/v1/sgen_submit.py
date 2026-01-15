# app/api/v1/sgen_submit.py

from fastapi import APIRouter, HTTPException

from app.models import (
    SGenErrorResponse,
    SGenSubmitRequest,
    SGenSubmitResponse,
)
from app.services.sgen_controller_client import SGenControllerClient

router = APIRouter(prefix="", tags=["sgen"])

controller = SGenControllerClient()


@router.post(
    "/submit",
    response_model=SGenSubmitResponse,
    responses={400: {"model": SGenErrorResponse}},
)
async def submit_job(req: SGenSubmitRequest):
    try:
        job = await controller.create_job(req)
        return SGenSubmitResponse(
            job_id=job.job_id,
            status=job.status,
            mode=job.mode,
            result=None,
            error=None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"sgen-controller unavailable: {exc}",
        )


@router.get(
    "/get_job_status/{job_id}",
    response_model=SGenSubmitResponse,
)
async def get_job_status(job_id: str):
    try:
        job = await controller.get_job(job_id)
        return SGenSubmitResponse(
            job_id=job.job_id,
            status=job.status,
            mode=job.mode,
            result=job.result,
            error=job.error,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"sgen-controller unavailable: {exc}",
        )
