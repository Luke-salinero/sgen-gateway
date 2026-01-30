from typing import Any, Mapping, Optional

from fastapi import HTTPException, requests

from app.config import get_settings


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

    try:
        return r.json()
    # System error
    except Exception as e:
        print(f"Expected JSON response but got:\n{r.text}")
        raise SystemExit(2) from e
