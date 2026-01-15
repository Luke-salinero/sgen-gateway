import httpx
import logging

from app.core import get_settings
from app.models.sgen import SGenSubmitRequest
from app.models.responses import JobCreatedResponse, JobResultResponse

logger = logging.getLogger(__name__)


class SGenControllerClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.sgen_controller_base_url
        self.timeout = settings.request_timeout_seconds

    async def create_job(self, req: SGenSubmitRequest) -> JobCreatedResponse:
        url = f"{self.base_url}/api/v1/jobs"
        logger.info("Forwarding job to sgen-controller", extra={"url": url})

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=req.model_dump())
            response.raise_for_status()
            return JobCreatedResponse(**response.json())

    async def get_job(self, job_id: str) -> JobResultResponse:
        url = f"{self.base_url}/api/v1/jobs/{job_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return JobResultResponse(**response.json())
