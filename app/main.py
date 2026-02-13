# app/api/main.py

import logging

from fastapi import FastAPI

from app.api.v1 import health, sgen_submit, results, status
from app.core import configure_logging, get_settings
from app.models import sgen


def create_app() -> FastAPI:
    """Application factory for the S-Gen gateway.

    Exposes the function used to construct and configure the FastAPI app
    """

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
    app.include_router(results.router)
    app.include_router(status.router)

    logger = logging.getLogger(__name__)
    logger.info(
        "S-Gen Gateway starting",
        extra={
            "mode": settings.sgen_mode,
            "compute_base_url": settings.compute_base_url,
        },
    )

    return app


app = create_app()
