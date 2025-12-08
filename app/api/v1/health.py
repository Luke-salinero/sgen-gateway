from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health_check():
    settings = get_settings()
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "ok",
        "mode": settings.sgen_mode,
    }
