from typing import Any, Mapping

from fastapi import HTTPException

from app.models import SGenSubmitRequest


def enforce_entitlements(
    req: SGenSubmitRequest, entitlements: Mapping[str, Any]
) -> None:
    limits = entitlements.get("limits")
    if not isinstance(limits, dict):
        raise HTTPException(
            status_code=502, detail="Entitlements response missing 'limits'"
        )

    max_n = limits.get("max_n")
    max_k = limits.get("max_k")
    # existential_only = limits.get("existential_only")

    if not isinstance(max_n, int) or not isinstance(max_k, int):
        raise HTTPException(
            status_code=502, detail="Entitlements limits missing max_n/max_k"
        )

    violations: list[str] = []

    if req.n > max_n:
        violations.append(f"n={req.n} exceeds max_n={max_n}")

    if req.k > max_k:
        violations.append(f"k={req.k} exceeds max_k={max_k}")

    # if existential_only and not req.existential:
    #     violations.append("non-existential mode is not allowed for this subject")

    if violations:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Request exceeds entitlements",
                "violations": violations,
                "tier": entitlements.get("tier"),
            },
        )
