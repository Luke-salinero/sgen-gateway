from functools import lru_cache
import os

from pydantic import Field
from pydantic_settings import BaseSettings

def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

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

    jwt_issuer: str = _env("JWT_ISSUER", "http://sgen-cape.bigsigma.tech/realms/sgen-test")
    jwt_audience: str = _env("JWT_AUDIENCE", "account")
    jwt_algorithms: tuple[str, ...] = tuple(
        os.getenv("JWT_ALGORITHMS", "RS256").split(",")
    )
    jwt_jwks_url: str = _env(
        "JWT_JWKS_URL",
        "http://sgen-cape.bigsigma.tech/realms/sgen-test/protocol/openid-connect/certs",
    )
    jwt_public_key: str = _env("JWT_PUBLIC_KEY", "public_key")

    # Optional: small clock skew leeway (seconds) for exp/nbf checks
    jwt_leeway_seconds: int = int(os.getenv("JWT_LEEWAY_SECONDS", "0"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Gets the settings"""
    return Settings()
