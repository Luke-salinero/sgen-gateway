from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # "mock" or "live"
    sgen_mode: str = Field(default="mock", alias="SGEN_MODE")

    service_name: str = "sgen-gateway"
    service_version: str = "0.1.0"

    compute_base_url: str = Field(
        default="http://127.0.0.1:9000",
        alias="SGEN_COMPUTE_BASE_URL",
    )

    request_timeout_seconds: int = Field(default=120, alias="SGEN_REQUEST_TIMEOUT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
