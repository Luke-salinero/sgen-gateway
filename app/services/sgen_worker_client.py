import os
from typing import Any, Dict, Optional

import httpx


class SGenWorkerClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (
            base_url or os.getenv("SGEN_WORKER_URL", "http://localhost:8002")
        ).rstrip("/")

    async def get_public_results_if_completed(
        self, *, job_id: str, subject_id: str
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/results/{job_id}"
        headers = {"Api-Key-Owner": subject_id, "Accept": "application/json"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 404:
            return None

        # bubble up other errors
        resp.raise_for_status()
        return None

    async def get_public_status_if_completed(
        self, *, job_id: str, subject_id: str
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/status/{job_id}"
        headers = {"Api-Key-Owner": subject_id, "Accept": "application/json"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 404:
            return None

        # bubble up other errors
        resp.raise_for_status()
        return None
