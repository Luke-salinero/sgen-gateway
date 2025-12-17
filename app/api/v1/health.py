from fastapi import APIRouter

from app.core import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health_check():
    """Allows users to check out the server/router health."""

    settings = get_settings()
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "ok",
        "mode": settings.sgen_mode,
    }
