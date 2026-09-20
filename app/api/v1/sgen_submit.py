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
from app.util import extract_bearer_token, authenticate_request

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
        ident = authenticate_request(authorization)

        if not ident:
            raise HTTPException(status_code=400, detail="Invalid bearer token")

        jwt = extract_bearer_token(authorization)
        entitlement = call_entitlements(
            jwt_token=jwt,
            request_id=None,
            timeout_s=15,
        )

        enforce_entitlements(req, entitlement)

        # Add block_size here
        payload = req.model_dump()
        payload["block_size"] = 3
        subject_id = entitlement.get("subject_id")

        job = await controller.create_job(payload, subject_id)

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

# NOTE: an earlier, unauthenticated `GET /get_job_status/{job_id}` lived here.
# It forwarded straight to sgen-controller with no bearer-token check and no
# entitlement/ownership check, so any caller who learned a job_id could read
# another subject's job status, result, and error payload. The authenticated,
# ownership-scoped equivalents are `status.router` (`/status/{job_id}`) and
# `results.router` (`/results/{job_id}`), which the SDK already uses
# exclusively (see sgen-sdk's client.py) - removed rather than patched.
