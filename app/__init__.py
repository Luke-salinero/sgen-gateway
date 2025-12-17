"""
Application factory for the S-Gen gateway.

Exposes the function used to construct and configure the FastAPI app.
"""

from .main import create_app

__all__ = [
    "create_app",
]
