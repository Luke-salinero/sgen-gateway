from typing import List, Tuple, Optional
from pydantic import BaseModel, Field, validator


def validate_bitstring(value: str, n: int) -> str:
    if not value.startswith("0b"):
        raise ValueError("Bitmask must start with '0b'")
    bits = value[2:]
    if any(c not in "01" for c in bits):
        raise ValueError("Bitmask may only contain 0 or 1")
    if len(bits) != n:
        raise ValueError(f"Bitmask must be {n} bits long")
    return value


class SGenSubmitRequest(BaseModel):
    n: int = Field(..., ge=1, le=2048)
    k: int = Field(..., ge=1)
    existential: bool = True
    prune_masks: List[str] = []
    find_masks: List[str] = []
    ranges: List[Tuple[str, str]] = []

    @validator("k")
    def validate_k(cls, v, values):
        n = values.get("n")
        if n is not None and v > n:
            raise ValueError("k must be ≤ n")
        return v

    @validator("prune_masks", "find_masks", each_item=True)
    def validate_masks(cls, mask, values):
        n = values.get("n")
        if n is None:
            return mask
        return validate_bitstring(mask, n)

    @validator("ranges", each_item=True)
    def validate_ranges(cls, pair, values):
        n = values.get("n")
        if n is None:
            return pair
        start, end = pair
        validate_bitstring(start, n)
        validate_bitstring(end, n)
        return pair


class SGenSubmitResponse(BaseModel):
    status: str = "ok"
    mode: str
    job_id: str
    results: List[str]
    n: int
    k: int


class SGenErrorResponse(BaseModel):
    status: str = "error"
    message: str
    mask: Optional[str] = None
    k: Optional[int] = None
