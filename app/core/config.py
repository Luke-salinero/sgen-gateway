from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Manages the base settings for SGen requests"""

    # "mock" or "live"
    sgen_mode: str = Field(default="mock", alias="SGEN_MODE")

    service_name: str = "sgen-gateway"
    service_version: str = "0.1.0"

    # NEW: points to the control-plane service
    sgen_controller_base_url: str = Field(
        default="http://127.0.0.1:8001",
        alias="SGEN_CONTROLLER_BASE_URL",
    )

    # OLD/legacy: keep for now to avoid breaking imports;
    compute_base_url: str = Field(
        default="http://127.0.0.1:9000",
        alias="SGEN_COMPUTE_BASE_URL",
    )

    entitlements_base_url: str = Field(
        default="http://127.0.0.1:8002",
        alias="SGEN_ENTITLEMENTS_BASE_URL",
    )

    request_timeout_seconds: int = Field(default=120, alias="SGEN_REQUEST_TIMEOUT")



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Gets the settings"""
    return Settings()
