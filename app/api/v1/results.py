from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.services.entitlement_request import call_entitlements
from app.services.sgen_worker_client import SGenWorkerClient
from app.util import extract_bearer_token, authenticate_request

worker = SGenWorkerClient()
router = APIRouter(prefix="", tags=["sgen"])


@router.get("/results/{job_id}", status_code=200)
async def get_results(
    job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    try:
        ident = authenticate_request(authorization)
        jwt = extract_bearer_token(authorization)

        entitlement = call_entitlements(jwt_token=jwt, request_id=None, timeout_s=15)
        subject_id = entitlement.get("subject_id")
        if not subject_id:
            raise HTTPException(
                status_code=403, detail="Missing subject_id in entitlements"
            )

        results = await worker.get_public_results_if_completed(
            job_id=job_id, subject_id=subject_id
        )

        if results is None:
            raise HTTPException(
                status_code=404, detail="Job not found or not completed"
            )
        return results

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"downstream unavailable: {exc}"
        ) from exc
