import logging

from fastapi import FastAPI

from app.api.v1 import health, jobs
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.v1 import sgen_submit



def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="S-Gen Gateway",
        version=settings.service_version,
        description="Gateway service for S-Gen, behind Cloudflare Tunnel.",
    )

    # Routers
    app.include_router(health.router)
    app.include_router(sgen_submit.router)
    app.include_router(jobs.router)

    logger = logging.getLogger(__name__)
    logger.info(
        "S-Gen Gateway starting",
        extra={"mode": settings.sgen_mode, "compute_base_url": settings.compute_base_url},
    )

    return app


app = create_app()
