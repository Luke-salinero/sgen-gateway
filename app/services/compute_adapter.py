import logging
import uuid
from typing import Optional

import httpx

from app.core.config import get_settings
from app.models.job import InternalJobRequest, InternalJobResult, JobStatus

logger = logging.getLogger(__name__)


class ComputeAdapter:
    def __init__(self, base_url: Optional[str] = None) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.compute_base_url
        self.timeout = settings.request_timeout_seconds

    async def run_job_mock(self, job: InternalJobRequest) -> InternalJobResult:
        """
        Mock implementation: returns a fake image URL / payload
        without touching any real compute.
        """
        logger.info("Running job in MOCK mode", extra={"job_id": job.job_id})

        fake_result = {
            "images": [
                {
                    "id": f"mock-{job.job_id}",
                    "url": f"https://example.com/mock/{job.job_id}.png",
                    "metadata": {
                        "seed": job.payload.seed or 123456,
                        "steps": job.payload.steps,
                        "resolution": job.payload.resolution,
                    },
                }
            ]
        }

        return InternalJobResult(
            job_id=job.job_id,
            status=JobStatus.MOCKED,
            result=fake_result,
            error=None,
        )

    async def run_job_live(self, job: InternalJobRequest) -> InternalJobResult:
        """
        Live implementation: talks to the real compute node over HTTP.
        This is where you’ll integrate with your S-Gen node via Tailscale.
        """
        url = f"{self.base_url}/internal/v1/jobs"
        logger.info(
            "Dispatching job to compute node",
            extra={"job_id": job.job_id, "url": url},
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=job.model_dump())
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.exception(
                    "Error calling compute node",
                    extra={"job_id": job.job_id, "error": str(exc)},
                )
                return InternalJobResult(
                    job_id=job.job_id,
                    status=JobStatus.FAILED,
                    result=None,
                    error={"code": "COMPUTE_UNAVAILABLE", "message": str(exc)},
                )

        data = response.json()
        # You can adapt this parsing once the compute API is concrete
        return InternalJobResult(
            job_id=data.get("job_id", job.job_id),
            status=data.get("status", JobStatus.COMPLETED),
            result=data.get("result"),
            error=data.get("error"),
        )


def generate_job_id() -> str:
    return str(uuid.uuid4())
