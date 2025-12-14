"""
services

Contains Class for running mock/live job and generating Job ID
"""

from .compute_adapter import (
    ComputeAdapter,
    generate_job_id,
)

__all__ = [
    "ComputeAdapter",
    "generate_job_id",
]
