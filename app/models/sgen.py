from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, validator


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
            v (int): Number of active bits in each binary pattern
            values (Dict): Dictionary of important values relating to the bitstring.

        Returns:
            v (int): Number of active bits in each binary pattern
        """

        n = values.get("n")
        if n is not None and v > n:
            raise ValueError("k must be ≤ n")
        if not (v > 0):
            # If k == 0, then our search space is [0].
            raise ValueError("k must be a positive integer")
        return v

    @validator("prune_masks", "find_masks", each_item=True)
    def validate_masks(cls, mask, values):
        """Validates the mask and returns whether it is a valid bitstring.

        Args:
            mask (str): A bitstring representing the mask
            values (Dict): Dictionary of important values relating to the bitstring.

        Returns:
            mask (str): Validated bitstring representing the mask
        """
        n = values.get("n")
        if n is None:
            return mask
        return validate_bitstring(mask, n)

    @validator("k", "prune_masks", "find_masks", each_item=True)
    def validate_maskActiveBits(cls, mask, v, values):
        """Validates the number of active bits in a mask

        Args:
            mask (str): A bitstring representing the mask
            v (int): Number of active bits in each binary pattern
            values (Dict): Dictionary of important values relating to the bitstring.


        Returns:
            mask (str): Validated bitstring representing the mask
        """

        n = values.get("n")
        if n is None:
            return mask

        maskActiveBits = mask.count("1")
        if maskActiveBits != v:
            raise ValueError("Bitmask active bits does not equal k!")

        return mask

    @validator("ranges", each_item=True)
    def validate_ranges(cls, pair, values):
        """Validates the ranges and returns whether the min/max
           of the range is a valid bitstring

        Args:
            pair (array): A bitstring pair representing the start and end of the range.
            values (Dict): Dictionary of important values relating to the bitstring.

        Returns:
            pair (array): Validated bitstring pair representing
                        the start and end of the range.
        """
        n = values.get("n")
        if n is None:
            return pair
        start, end = pair

        validate_bitstring(start, n)
        validate_bitstring(end, n)

        # Convert to bits
        startBit = int(start, 0)
        endBit = int(end, 0)

        if not (startBit <= endBit):
            raise ValueError("Start of range is > end of range!")

        return pair

    @validator("ranges", "k", each_item=True)
    def validate_rangeActiveBits(cls, pair, v, values):
        """Validates the ranges and whether they meet boundary min/maxs.

        Args:
            pair (array): A bitstring pair representing the start and end of the range.
            values (Dict): Dictionary of important values relating to the bitstring.

        Returns:
            pair (array): Validated bitstring pair representing
                        the start and end of the range.
        """
        n = values.get("n")
        if n is None:
            return pair
        start, end = pair

        # Convert to bits
        startBit = int(start, 0)
        endBit = int(end, 0)

        maxBit = "0b" + "1" * v + "0" * (n - v)
        minBit = "0b" + "0" * (n - v) + "1" * v

        intMinBit = int(minBit, 0)
        intMaxBit = int(maxBit, 0)

        if startBit < intMinBit:
            raise ValueError(f"Start of range should be atleast {minBit}")
        if endBit > intMaxBit:
            raise ValueError(f"End of range should be atleast {maxBit}")

        return pair

    @validator("ranges")
    def validate_rangeOverlap(cls, ranges, values):
        """Validates the ranges and returns whether the ranges overlap

        Args:
            ranges (array): Array of bitstring pairs representing
                           the start and end of the range.
            values (Dict): Dictionary of important values relating to the bitstring.

        Returns:
            ranges (array): Array of Validated bitstring pairs representing
                        the start and end of the range.
        """
        n = values.get("n")
        if n is None:
            return ranges

        if len(ranges) <= 1:
            return ranges
        sortedArray = []
        # Sort by lower boundary
        sortedArray.sort(key=lambda x: int(x[0], 0))
        overlaps = []
        previousRange = sortedArray[0]

        # Loop over ranges and see whether next lower boundary
        # falls in the range of the previous lower boundar
        # to the largest upper boundary we've seen
        for currentRange in sortedArray[1:]:
            previousStart, previousEnd = previousRange
            currentStart, currentEnd = currentRange

            if currentStart <= previousEnd:
                overlaps.append((previousRange, currentRange))
                previousRange = (previousStart, max(previousEnd, currentEnd))
            else:
                previousRange = currentRange
        if len(overlaps) != 0:
            # Instead of raising a value error, we could collapse the
            # overlapping ranges into one range.
            raise ValueError(f"There are overlapping ranges!\n{overlaps}")
        return ranges

    @validator("ranges", "prune_masks", "find_masks", each_item=True)
    def validate_masksInRanges(cls, pair, mask, values):
        """Validates the mask and returns whether
           they are within the range boundaries

        Args:
            mask (str): A bitstring representing the mask
            values (Dict): Dictionary of important values relating to the bitstring.

        Returns:
            mask (str): Validated bitstring pair representing
                        the start and end of the range.
        """
        n = values.get("n")
        if n is None:
            return mask
        start, end = pair

        # Convert to integers, see if mask is in range
        startBit = int(start, 0)
        endBit = int(end, 0)
        maskBit = int(mask, 0)

        if not (startBit <= maskBit and maskBit <= endBit):
            raise ValueError("Bitmask is not in the range!")

        return mask


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
