from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, validator


def validate_bitstring(value: str, n: int) -> str:
    """Validates the input bitstring and raises an error if its not allowed

    Args:
        value : Initial bitstring
        n : Bitwidth of the bitstring

    Returns:
        value: Initial bitstring
    """

    if not value.startswith("0b"):
        raise ValueError("Bitmask must start with '0b'")
    bits = value[2:]
    if any(c not in "01" for c in bits):
        raise ValueError("Bitmask may only contain 0 or 1")
    if len(bits) != n:
        raise ValueError(f"Bitmask must be {n} bits long")
    return value


class SGenSubmitRequest(BaseModel):
    """Runs the submitted Basemodel through validation checks

    Attributes:
        n (int): Bit width of the binary strings to process
        k (int): Number of active bits in each binary pattern
        existential (boolean): Mode flag to toggle existential processing
        prune_masks (array): List of binary strings representing masks
                             to prune certain data
        find_masks (array): List of binary strings representing masks
                            to find specific data
        ranges (array): List of [start,end] pairs defining processing ranges
    """

    n: int = Field(..., ge=1, le=2048)
    k: int = Field(..., ge=1)
    existential: bool = True
    prune_masks: List[str] = []
    find_masks: List[str] = []
    ranges: List[Tuple[str, str]] = []

    @validator("k")
    def validate_k(cls, v, values):
        """Validates the number of active bits (must be LEQ than bitwidth)

        Args:
            v: Number of active bits in each binary pattern
            values: Dictionary of important values relating to the bitstring.

        Returns:
            v: Number of active bits in each binary pattern
        """

        n = values.get("n")
        if n is not None and v > n:
            raise ValueError("k must be ≤ n")
        return v

    @validator("prune_masks", "find_masks", each_item=True)
    def validate_masks(cls, mask, values):
        """Validates the mask and returns whether it is a valid bitstring.

        Args:
            mask: A bitstring representing the mask
            values: Dictionary of important values relating to the bitstring.

        Returns:
            mask: Validated bitstring representing the mask
        """
        n = values.get("n")
        if n is None:
            return mask
        return validate_bitstring(mask, n)

    @validator("ranges", each_item=True)
    def validate_ranges(cls, pair, values):
        """Validates the ranges and returns whether the min/max
           of the range is a valid bitstring

        Args:
            pair: A bitstring pair representing the start and end of the range.
            values: Dictionary of important values relating to the bitstring.

        Returns:
            mask: Validated bitstring pair representing
                        the start and end of the range.
        """
        n = values.get("n")
        if n is None:
            return pair
        start, end = pair
        validate_bitstring(start, n)
        validate_bitstring(end, n)
        return pair


class SGenSubmitResponse(BaseModel):
    """Information pertaining to the SGen product"""

    status: str = "ok"
    mode: str
    job_id: str
    results: List[str]
    n: int
    k: int


class SGenErrorResponse(BaseModel):
    """Information pertaining to any SGen error encountered"""

    status: str = "error"
    message: str
    mask: Optional[str] = None
    k: Optional[int] = None
