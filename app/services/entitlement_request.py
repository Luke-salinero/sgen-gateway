from typing import Any, Mapping, Optional

import requests
from fastapi import HTTPException

from app.core.config import get_settings


def call_entitlements(
    *,
    jwt_token: str,
    request_id: Optional[str] = None,
    timeout_s: int = 15,
) -> Mapping[str, Any]:

    settings = get_settings()
    url = settings.entitlements_base_url + "/v1/entitlements"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/json",
    }
    if request_id:
        headers["X-Request-Id"] = request_id

    try:
        r = requests.get(url, headers=headers, timeout=timeout_s)
    # Network error
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Entitlements request failed: {exc}"
        ) from exc

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Entitlements error {r.status_code}: {r.text}"
        )

    if "application/json" not in r.headers.get("Content-Type", ""):
        raise HTTPException(
            status_code=502,
            detail="Entitlements returned non-JSON response"
        )

    data = r.json()

    try:
        return data
    # System error
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "service": "entitlements",
                "error": "Invalid response",
                "status": r.status_code if r else None,
                "body": r.text if r else None,
            },
        ) from e
