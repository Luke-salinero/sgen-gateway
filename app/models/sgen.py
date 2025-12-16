from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


def validate_bitstring(value: str, n: int) -> str:
    """Validates the input bitstring and raises an error if its not allowed

    Args:
        value (str): Initial bitstring
        n (int): Bitwidth of the bitstring

    Returns:
        value (str): Initial bitstring
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

    model_config = {"strict": True}

    n: int = Field(..., ge=1, le=2048)
    k: int = Field(..., ge=1)
    existential: bool = True
    prune_masks: List[str] = []
    find_masks: List[str] = []
    ranges: List[Tuple[str, str]] = []

    @field_validator("k", mode="after")
    @classmethod
    def validate_k(cls, v, info):
        """
        Validate `k`, the number of active bits in a pattern, against `n`,
        the total bit-width of the binary representation.

        Args:
            v (int): Number of active bits required.
            info (ValidationInfo): Access to other validated fields, including `n`.

        Returns:
            int: Validated value of `k`.
        """
        n = info.data.get("n")
        if n is not None and v > n:
            raise ValueError("k must be ≤ n")
        if v <= 0:
            raise ValueError("k must be a positive integer")
        return v

    @field_validator("prune_masks", "find_masks", mode="after")
    @classmethod
    def validate_masks(cls, masks, info):
        """
        Validate that each prune/find mask is a binary string of length `n`,
        representing a fixed-width bitmask.

        Args:
            masks (List[str]): List of binary mask strings.
            info (ValidationInfo): Access to `n` (bit-width).

        Returns:
            List[str]: Validated mask list.
        """
        n = info.data.get("n")
        if n is None:
            return masks
        return [validate_bitstring(mask, n) for mask in masks]

    @field_validator("ranges", mode="after")
    @classmethod
    def validate_ranges(cls, ranges, info):
        """
        Validate each range defines a valid inclusive interval between two
        `n`-bit binary values, with start less than or equal to end.

        Args:
            ranges (List[Tuple[str, str]]): Bitstring range bounds.
            info (ValidationInfo): Access to `n` (bit-width).

        Returns:
            List[Tuple[str, str]]: Validated ranges.
        """
        n = info.data.get("n")
        if n is None:
            return ranges

        for start, end in ranges:
            validate_bitstring(start, n)
            validate_bitstring(end, n)

            if int(start, 0) >= int(end, 0):
                raise ValueError("Start of range is >= end of range!")

        return ranges

    @field_validator("ranges", mode="after")
    @classmethod
    def validate_rangeOverlap(cls, ranges, info):
        """
        Ensure that defined binary ranges do not overlap,
        preventing ambiguous or duplicated coverage.

        Args:
            ranges (List[Tuple[str, str]]): Bitstring range bounds.
            info (ValidationInfo): Validation context.

        Returns:
            List[Tuple[str, str]]: Non-overlapping ranges.
        """
        if len(ranges) <= 1:
            return ranges

        sorted_ranges = sorted(ranges, key=lambda r: int(r[0], 0))
        _, prev_end = sorted_ranges[0]

        for start, end in sorted_ranges[1:]:
            if int(start, 0) <= int(prev_end, 0):
                raise ValueError("There are overlapping ranges!")
            _, prev_end = start, end

        return ranges

    @model_validator(mode="after")
    def validate_maskActiveBits(self):
        """
        Ensure all prune and find masks contain exactly `k` active (set) bits,
        where `k` defines the required sparsity of each pattern.

        Returns:
            SGenSubmitRequest: Validated model instance.
        """
        for mask in self.prune_masks + self.find_masks:
            if mask.count("1") != self.k:
                raise ValueError("Bitmask active bits does not equal k!")
        return self

    @model_validator(mode="after")
    def validate_rangeActiveBits(self):
        """
        Ensure all ranges lie within the minimum and maximum values
        allowed by `n` (bit-width) and `k` (active bit count).
        """
        max_bit = int("0b" + "1" * self.k + "0" * (self.n - self.k), 0)
        min_bit = int("0b" + "0" * (self.n - self.k) + "1" * self.k, 0)

        for start, end in self.ranges:
            if int(start, 0) < min_bit:
                raise ValueError(f"Start of range should be atleast {bin(min_bit)}")
            if int(end, 0) > max_bit:
                raise ValueError(f"End of range should be atleast {bin(max_bit)}")

        return self

    @model_validator(mode="after")
    def validate_masksInRanges(self):
        """
        Ensure each prune and find mask falls within at least one
        of the defined binary ranges.
        """
        if not self.ranges:
            return self

        range_bounds = [(int(s, 0), int(e, 0)) for s, e in self.ranges]

        def in_any_range(value: int) -> bool:
            return any(start <= value <= end for start, end in range_bounds)

        for mask in self.prune_masks + self.find_masks:
            if not in_any_range(int(mask, 0)):
                raise ValueError("Bitmask is not in the range!")

        return self


class SGenSubmitResponse(BaseModel):
    """Information pertaining to the SGen product

    Args:
        BaseModel
    """

    status: str = "ok"
    mode: str
    job_id: str
    results: List[str]
    n: int
    k: int


class SGenErrorResponse(BaseModel):
    """Information pertaining to any SGen error encountered

    Args:
        BaseModel
    """

    status: str = "error"
    message: str
    mask: Optional[str] = None
    k: Optional[int] = None
