# app/api/v1/sgen_submit.py
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.models import (
    SGenErrorResponse,
    SGenSubmitRequest,
    SGenSubmitResponse,
)
from app.services.entitlement_enforce import enforce_entitlements
from app.services.entitlement_request import call_entitlements
from app.services.sgen_controller_client import SGenControllerClient
from app.util.extract_bearer import extract_bearer_token

router = APIRouter(prefix="", tags=["sgen"])

controller = SGenControllerClient()


@router.post(
    "/submit",
    response_model=SGenSubmitResponse,
    responses={400: {"model": SGenErrorResponse}},
)
async def submit_job(
    req: SGenSubmitRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):

    try:
        jwt = extract_bearer_token(authorization)
        entitlement = await call_entitlements(
            jwt_token=jwt,
            request_id=None,
            timeout_s=15,
        )
        enforce_entitlements(req, entitlement)

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
        ) from exc


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
        ) from exc
