import random
import unittest
from typing import Dict, List, Tuple

from pydantic import ValidationError

# Adjust import path to match your repo layout:
# If your model is in app/models/sgen.py:
from app.models import SGenSubmitRequest, validate_bitstring


def to_bit(x: int, n: int) -> str:
    """Format integer as fixed-width bitstring with 0b prefix."""
    return "0b" + format(x, f"0{n}b")


def min_max_for_nk(n: int, k: int) -> Tuple[int, int]:
    """Return integer min/max bounds implied by (n,k) rangeActiveBits rule."""
    max_bit = int("0b" + "1" * k + "0" * (n - k), 0)
    min_bit = int("0b" + "0" * (n - k) + "1" * k, 0)
    return min_bit, max_bit


def make_valid_payload(rng: random.Random, n: int, k: int) -> Dict:
    """
    Generate a payload that should be accepted by the current model logic.
    Notes:
      - ranges require start < end (strict).
      - if min_bit == max_bit (e.g., k==n), ranges cannot exist; keep ranges empty.
      - masks must be valid bitstrings, popcount==k, and (if ranges exist)
        inside at least one range.
    """
    min_bit, max_bit = min_max_for_nk(n, k)

    if min_bit == max_bit:
        # k == n: any range would violate start < end inside [min,max]
        ranges: List[Tuple[str, str]] = []
        # Choose the only valid k==n mask (all ones)
        masks = [to_bit(min_bit, n)]
    else:
        # Use a single wide allowed range for guaranteed "masks in range"
        ranges = [(to_bit(min_bit, n), to_bit(max_bit, n))]
        # Use endpoints for guaranteed popcount==k and in-range
        masks = [to_bit(min_bit, n), to_bit(max_bit, n)]

    prune_masks = []
    find_masks = []
    # Randomly distribute masks into prune/find for coverage
    for m in masks:
        (prune_masks if rng.random() < 0.5 else find_masks).append(m)

    return {
        "n": n,
        "k": k,
        "existential": rng.choice([True, False]),
        "prune_masks": prune_masks,
        "find_masks": find_masks,
        "ranges": ranges,
    }


def mutate_payload_to_break_one_rule(rng: random.Random, payload: Dict) -> Dict:
    """
    Take a known-valid payload and mutate it to violate exactly one major rule.
    Returns a new payload.
    """
    p = {**payload}
    rule = rng.choice(
        [
            "bad_prefix_mask",
            "bad_char_mask",
            "bad_len_mask",
            "mask_popcount_mismatch",
            "range_start_ge_end",
            "overlapping_ranges",
            "range_below_min",
            "range_above_max",
            "mask_outside_ranges",
            "k_gt_n",
        ]
    )

    n = p["n"]
    k = p["k"]
    min_bit, max_bit = min_max_for_nk(n, k)

    # Ensure lists exist
    p["prune_masks"] = list(p.get("prune_masks", []))
    p["find_masks"] = list(p.get("find_masks", []))
    p["ranges"] = list(p.get("ranges", []))

    def ensure_some_mask():
        if not p["prune_masks"] and not p["find_masks"]:
            p["find_masks"] = [to_bit(min_bit, n)]

    if rule == "k_gt_n":
        p["k"] = n + 1
        return p

    if rule in {
        "bad_prefix_mask",
        "bad_char_mask",
        "bad_len_mask",
        "mask_popcount_mismatch",
        "mask_outside_ranges",
    }:
        ensure_some_mask()

    if rule == "bad_prefix_mask":
        # remove 0b prefix
        if p["prune_masks"]:
            p["prune_masks"][0] = p["prune_masks"][0].replace("0b", "00", 1)
        else:
            p["find_masks"][0] = p["find_masks"][0].replace("0b", "00", 1)
        return p

    if rule == "bad_char_mask":
        # inject invalid char
        target = "prune_masks" if p["prune_masks"] else "find_masks"
        m = p[target][0]
        p[target][0] = m[:2] + "0" * (n - 1) + "X"
        return p

    if rule == "bad_len_mask":
        # wrong length bits (n-1)
        target = "prune_masks" if p["prune_masks"] else "find_masks"
        p[target][0] = "0b" + "0" * (n - 1)
        return p

    if rule == "mask_popcount_mismatch":
        # set mask to all zeros => popcount 0 != k
        target = "prune_masks" if p["prune_masks"] else "find_masks"
        p[target][0] = "0b" + "0" * n
        return p

    # range-related mutations
    if rule in {
        "range_start_ge_end",
        "overlapping_ranges",
        "range_below_min",
        "range_above_max",
        "mask_outside_ranges",
    }:
        if min_bit == max_bit:
            # Force a range to exist (will be invalid under start<end anyway)
            p["ranges"] = [(to_bit(min_bit, n), to_bit(min_bit, n))]
        elif not p["ranges"]:
            p["ranges"] = [(to_bit(min_bit, n), to_bit(max_bit, n))]

    if rule == "range_start_ge_end":
        # start == end (explicitly rejected by >= check)
        p["ranges"] = [(to_bit(min_bit, n), to_bit(min_bit, n))]
        return p

    if rule == "overlapping_ranges":
        if min_bit == max_bit:
            # already invalid; keep it simple
            p["ranges"] = [(to_bit(min_bit, n), to_bit(min_bit, n))]
        else:
            # overlap: [min, min+2], [min+1, min+3]
            a = min_bit
            p["ranges"] = [
                (to_bit(a, n), to_bit(min(a + 2, max_bit), n)),
                (to_bit(min(a + 1, max_bit), n), to_bit(min(a + 3, max_bit), n)),
            ]
        return p

    if rule == "range_below_min":
        # start below min_bit
        low = max(0, min_bit - 1)
        hi = min_bit + 1 if min_bit + 1 <= (1 << n) - 1 else min_bit
        p["ranges"] = [(to_bit(low, n), to_bit(hi, n))]
        return p

    if rule == "range_above_max":
        # end above max_bit
        hi = min((1 << n) - 1, max_bit + 1)
        lo = max_bit - 1 if max_bit - 1 >= 0 else 0
        p["ranges"] = [(to_bit(lo, n), to_bit(hi, n))]
        return p

    if rule == "mask_outside_ranges":
        # Ensure we have a range, then place a mask outside it
        if min_bit != max_bit and p["ranges"]:
            p["ranges"] = [(to_bit(min_bit, n), to_bit(min_bit + 1, n))]
            # mask far above end
            outside = min((1 << n) - 1, min_bit + 10)
            # but ensure it's outside the tiny range
            if outside <= min_bit + 1:
                outside = min((1 << n) - 1, min_bit + 2)
            p["find_masks"] = [to_bit(outside, n)]
        else:
            # k==n case: no ranges normally; force a range then a different mask
            p["ranges"] = [(to_bit(min_bit, n), to_bit(min_bit, n))]
            p["find_masks"] = ["0b" + "0" * n]
        return p

    return p


class TestValidateBitstring(unittest.TestCase):
    def test_requires_0b_prefix(self):
        with self.assertRaisesRegex(ValueError, r"must start with '0b'"):
            validate_bitstring("1010", 4)
        # WHY: Missing prefix can silently break int(..., 0) parsing assumptions.

    def test_rejects_non_binary_chars(self):
        with self.assertRaisesRegex(ValueError, r"may only contain 0 or 1"):
            validate_bitstring("0b10a0", 4)
        # WHY: Non-binary chars can bypass downstream numeric logic or crash later.

    def test_rejects_wrong_length(self):
        with self.assertRaisesRegex(ValueError, r"must be 4 bits long"):
            validate_bitstring("0b101", 4)
        # WHY: Wrong-width masks misalign with n-bit operations and comparisons.

    def test_accepts_valid_bitstring(self):
        self.assertEqual(validate_bitstring("0b1010", 4), "0b1010")
        # WHY: Positive test ensures validators don’t “win” by rejecting everything.

    def test_accepts_min_width_n_1(self):
        self.assertEqual(validate_bitstring("0b0", 1), "0b0")
        self.assertEqual(validate_bitstring("0b1", 1), "0b1")
        # WHY: Smallest valid n often exposes off-by-one logic errors.


class TestSGenSubmitRequest(unittest.TestCase):
    def assert_accepted(self, payload: Dict):
        try:
            SGenSubmitRequest(**payload)
        except Exception as e:
            self.fail(
                f"Expected acceptance but got {type(e).__name__}:{e}\nPayload={payload}"
            )

    def assert_rejected(self, payload: Dict, pattern: str):
        with self.assertRaisesRegex(ValidationError, pattern):
            SGenSubmitRequest(**payload)

    def test_k_must_not_exceed_n(self):
        payload = {
            "n": 4,
            "k": 5,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"k must be")
        # WHY: k>n makes “k ones in n bits” impossible and breaks bound math.

    def test_masks_must_have_valid_bitstring_format(self):
        payload = {
            "n": 4,
            "k": 2,
            "existential": True,
            "prune_masks": ["1111"],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"must start with '0b'")
        # WHY: Bad formats should fail early instead of poisoning later validators.

    def test_masks_must_match_bitwidth_n(self):
        payload = {
            "n": 4,
            "k": 2,
            "existential": True,
            "prune_masks": ["0b111"],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"must be 4 bits long")
        # WHY: Wrong-width masks undermine all range and popcount invariants.

    def test_ranges_require_start_strictly_less_than_end(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b0001", "0b0001")],
        }
        self.assert_rejected(payload, r"Start of range is .* end of range")
        # WHY: start>=end yields empty/invalid processing intervals.

    def test_ranges_reject_invalid_bitstrings(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b0002", "0b0011")],
        }
        self.assert_rejected(payload, r"may only contain 0 or 1")
        # WHY: Invalid range endpoints can crash integer conversion or comparisons.

    def test_rejects_overlapping_ranges(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b0001", "0b0011"), ("0b0011", "0b0100")],
        }
        self.assert_rejected(payload, r"overlapping ranges")
        # WHY: Overlaps can cause duplicate coverage and ambiguous results.

    def test_masks_must_have_exactly_k_ones(self):
        payload = {
            "n": 4,
            "k": 2,
            "existential": True,
            "prune_masks": ["0b1111"],  # 4 ones
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"active bits does not equal k")
        # WHY: Wrong popcount invalidates the intended search-space constraints.

    def test_ranges_must_respect_min_max_bounds_from_nk(self):
        # n=6,k=5 => min_bit is 0b011111 (31); start=0b000001 is too small
        payload = {
            "n": 6,
            "k": 5,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b000001", "0b011111")],
        }
        self.assert_rejected(payload, r"Start of range should be atleast")
        # WHY: Out-of-bound ranges allow impossible values past constraints.

    def test_masks_must_fall_inside_at_least_one_range_when_ranges_present(self):
        payload = {
            "n": 6,
            "k": 2,
            "existential": True,
            "prune_masks": [],
            "find_masks": ["0b000011"],  # popcount==2, but we’ll make range exclude it
            "ranges": [("0b000100", "0b000110")],
        }
        self.assert_rejected(payload, r"Bitmask is not in the range")
        # WHY: Masks outside all ranges produce undefined filtering behavior.

    def test_accepts_minimal_valid_payload(self):
        payload = make_valid_payload(random.Random(1), n=4, k=2)
        self.assert_accepted(payload)
        # WHY: You need “good path” coverage to prove rejections are meaningful.


class TestFuzzAndBypass(unittest.TestCase):
    def assert_accepted(self, payload: Dict):
        try:
            SGenSubmitRequest(**payload)
        except Exception as e:
            self.fail(
                f"Expected acceptance but got {type(e).__name__}:{e}\nPayload={payload}"
            )

    def assert_rejected(self, payload: Dict):
        with self.assertRaises(ValidationError):
            SGenSubmitRequest(**payload)

    def test_block_bulk_valid_inputs(self):
        rng = random.Random(1337)
        cases = 500

        for _ in range(cases):
            n = rng.randint(1, 2048)
            k = rng.randint(1, n)  # enforce k<=n for “valid” generator
            payload = make_valid_payload(rng, n=n, k=k)
            self.assert_accepted(payload)
        # WHY: Bulk valid coverage catches accidental over-rejection and ordering bugs.

    def test_block_bulk_invalid_inputs(self):
        rng = random.Random(7331)
        cases = 1000

        for _ in range(cases):
            n = rng.randint(1, 2048)
            k = rng.randint(1, n)
            good = make_valid_payload(rng, n=n, k=k)
            bad = mutate_payload_to_break_one_rule(rng, good)
            self.assert_rejected(bad)
        # WHY: Bulk “one-rule breaks” finds bypasses where invalid data slips through.

    def test_boundary_stress_varied_nk(self):
        rng = random.Random(2025)
        boundary_pairs = [(1, 1), (2, 1), (5, 5), (8, 1), (8, 7), (16, 16), (32, 16)]

        for n, k in boundary_pairs:
            payload = make_valid_payload(rng, n=n, k=k)
            self.assert_accepted(payload)
        # WHY: Boundaries (k==1, k==n, etc.) expose off-by-one and empty-window issues.


class TestAdversarialCrashAndBypass(unittest.TestCase):
    def assert_rejected(self, payload, pattern=None):
        if pattern:
            with self.assertRaisesRegex(ValidationError, pattern):
                SGenSubmitRequest(**payload)
        else:
            with self.assertRaises(ValidationError):
                SGenSubmitRequest(**payload)

    def assert_rejected_not_crash(self, payload):
        # Ensures we get a ValidationError (controlled failure),
        # not a raw Python exception.
        try:
            SGenSubmitRequest(**payload)
            self.fail(f"Expected rejection but payload was accepted: {payload}")
        except ValidationError:
            return
        except Exception as e:
            self.fail(
                f"Unexpected crash type {type(e).__name__}: {e}\nPayload={payload}"
            )

    # --------------------------
    # Pydantic coercion & type traps
    # --------------------------

    def test_masks_none_item_is_rejected_cleanly(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [None],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected_not_crash(payload)
        # WHY: None should never reach bitstring ops (would cause AttributeError).

    def test_masks_int_item_is_rejected_cleanly(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [123],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected_not_crash(payload)
        # WHY: Type coercion can turn ints into strings that bypass assumptions.

    def test_ranges_wrong_shape_singleton_tuple(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b0001",)],
        }
        self.assert_rejected_not_crash(payload)
        # WHY: Unpack errors must surface as validation failures, not crashes.

    def test_ranges_wrong_shape_triple_tuple(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b0000", "0b0001", "0b0010")],
        }
        self.assert_rejected_not_crash(payload)
        # WHY: Extra elements should not be silently ignored or cause runtime errors.

    def test_ranges_item_none(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [(None, "0b0001")],
        }
        self.assert_rejected_not_crash(payload)
        # WHY: Prevents `.startswith` / `int(...,0)` crashes if typing isn’t enforced.

    # --------------------------
    # Bitstring format bypass attempts
    # --------------------------

    def test_mask_with_whitespace_prefix(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [" 0b0001"],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"must start with '0b'")
        # WHY: Leading whitespace should not be accepted as a valid binary prefix.

    def test_mask_with_trailing_whitespace(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": ["0b0001 "],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"may only contain 0 or 1")
        # WHY: Trailing whitespace can pass naive prefix checks but breaks parsing.

    def test_mask_uppercase_prefix_rejected(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": ["0B0001"],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"must start with '0b'")
        # WHY: Case sensitivity prevents accepting ambiguous formats.

    def test_mask_with_unicode_digits(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": ["0b０００１"],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"may only contain 0 or 1")
        # WHY: Unicode lookalike digits can fool humans and break strict parsing.

    def test_mask_empty_bits_rejected(self):
        payload = {
            "n": 1,
            "k": 1,
            "existential": True,
            "prune_masks": ["0b"],
            "find_masks": [],
            "ranges": [],
        }
        self.assert_rejected(payload, r"must be 1 bits long")
        # WHY: Empty payloads can crash numeric conversion if not blocked early.

    # --------------------------
    # Range boundary and overlap edges
    # --------------------------

    def test_range_start_equal_end_rejected(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b0001", "0b0001")],
        }
        self.assert_rejected(payload, r"Start of range is .* end of range")
        # WHY: Zero-length ranges can create dead zones or infinite loops downstream.

    def test_overlap_exact_touch_is_rejected(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b0001", "0b0010"), ("0b0010", "0b0011")],
        }
        self.assert_rejected(payload, r"overlapping ranges")
        # WHY: Boundary-touch overlaps are a classic off-by-one ambiguity.

    def test_ranges_unsorted_input_still_detects_overlap(self):
        payload = {
            "n": 4,
            "k": 1,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b0010", "0b0011"), ("0b0001", "0b0010")],
        }
        self.assert_rejected(payload, r"overlapping ranges")
        # WHY: Overlap logic must be order-independent to avoid bypasses.

    # --------------------------
    # Min/max bound rule stress (n,k dependent)
    # --------------------------

    def test_range_min_bound_blocks_small_start(self):
        # n=6,k=5 => min_bit=0b011111; start below must fail
        payload = {
            "n": 6,
            "k": 5,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b000001", "0b011111")],
        }
        self.assert_rejected(payload, r"Start of range should be atleast")
        # WHY: Without this, “valid space” constraints are meaningless.

    def test_range_max_bound_blocks_large_end(self):
        # n=6,k=5 => max_bit=0b111110; end above must fail
        payload = {
            "n": 6,
            "k": 5,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b011111", "0b111111")],
        }
        self.assert_rejected(
            payload, r"End of range should be atleast|End of range should be"
        )
        # WHY: Upper bound errors can allow impossible patterns into computation.

    def test_k_equal_n_all_ranges_impossible(self):
        # For k==n, min_bit == max_bit so any start<end inside [min,max] is impossible.
        payload = {
            "n": 5,
            "k": 5,
            "existential": True,
            "prune_masks": [],
            "find_masks": [],
            "ranges": [("0b11111", "0b11111")],
        }
        self.assert_rejected(payload, r"Start of range is .* end of range")
        # WHY: This catches the subtle “valid bounds but impossible strict interval”
        # case.

    # --------------------------
    # Masks-in-ranges bypass attempts
    # --------------------------

    def test_mask_outside_all_ranges_rejected(self):
        payload = {
            "n": 6,
            "k": 2,
            "existential": True,
            "prune_masks": [],
            "find_masks": ["0b000011"],  # popcount==2
            "ranges": [("0b000100", "0b000110")],  # excludes 0b000011
        }
        self.assert_rejected(payload, r"Bitmask is not in the range")
        # WHY: Masks must not silently escape the intended search space.

    def test_mask_equal_range_start_is_allowed(self):
        payload = {
            "n": 6,
            "k": 2,
            "existential": True,
            "prune_masks": [],
            "find_masks": ["0b000011"],
            "ranges": [("0b000011", "0b000111")],
        }
        SGenSubmitRequest(**payload)
        # WHY: Inclusive endpoints are expected; off-by-one would reject valid values.

    def test_mask_equal_range_end_is_allowed(self):
        payload = {
            "n": 6,
            "k": 2,
            "existential": True,
            "prune_masks": [],
            "find_masks": ["0b000110"],  # 2 active bits
            "ranges": [("0b000011", "0b000110")],
        }
        SGenSubmitRequest(**payload)

    # --------------------------
    # Pathological size / robustness (fast but meaningful)
    # --------------------------

    def test_large_n_with_simple_masks_no_ranges(self):
        # Keep it cheap: no ranges means no huge min/max scanning across ranges.
        n = 2048
        payload = {
            "n": n,
            "k": 1,
            "existential": True,
            "prune_masks": ["0b" + "0" * (n - 1) + "1"],
            "find_masks": [],
            "ranges": [],
        }
        SGenSubmitRequest(**payload)
        # WHY: Large n should not cause accidental quadratic behavior or crashes.

    def test_large_n_wrong_length_mask_rejected(self):
        n = 128
        payload = {
            "n": n,
            "k": 1,
            "existential": True,
            "prune_masks": ["0b1"],
            "find_masks": ["0b01"],
            "ranges": [],
        }
        self.assert_rejected(payload, r"must be 128 bits long")
        # WHY: Large widths amplify length bugs that might slip past small tests.


"""Typing-focused unit tests for SGenSubmitRequest inputs."""


def base_payload() -> Dict:
    """Smallest-ish payload that should pass, used as a starting point."""
    return {
        "n": 4,
        "k": 1,
        "existential": True,
        "prune_masks": [],
        "find_masks": [],
        "ranges": [],
    }


class TestTypingIssuesAllFields(unittest.TestCase):
    def assert_rejected_not_crash(self, payload: Dict):
        """Reject via ValidationError only; never allow raw exceptions."""
        try:
            SGenSubmitRequest(**payload)
            self.fail(f"Expected ValidationError but was accepted: {payload}")
        except ValidationError:
            return
        except Exception as e:  # broad by design in tests
            self.fail(f"Unexpected crash {type(e).__name__}: {e}\nPayload={payload}")

    # -------------------------
    # n typing issues
    # -------------------------

    def test_n_none_rejected(self):
        p = base_payload()
        p["n"] = None
        self.assert_rejected_not_crash(p)
        # WHY: None must not reach bitwidth-dependent math/string checks.

    def test_n_string_rejected(self):
        p = base_payload()
        p["n"] = "4"
        self.assert_rejected_not_crash(p)
        # WHY: String n can enable unexpected coercion or wrong bounds.

    def test_n_float_rejected(self):
        p = base_payload()
        p["n"] = 4.5
        self.assert_rejected_not_crash(p)
        # WHY: Float width is nonsensical and can break formatting/length logic.

    def test_n_bool_rejected(self):
        p = base_payload()
        p["n"] = True
        self.assert_rejected_not_crash(p)
        # WHY: bool is an int subclass; accepting it silently is a classic footgun.

    # -------------------------
    # k typing issues
    # -------------------------

    def test_k_none_rejected(self):
        p = base_payload()
        p["k"] = None
        self.assert_rejected_not_crash(p)
        # WHY: None must not reach popcount comparisons.

    def test_k_string_rejected(self):
        p = base_payload()
        p["k"] = "1"
        self.assert_rejected_not_crash(p)
        # WHY: String k can cause implicit coercion and bypass “k<=n” intent.

    def test_k_float_rejected(self):
        p = base_payload()
        p["k"] = 1.1
        self.assert_rejected_not_crash(p)
        # WHY: Non-integer active-bit counts are invalid but can slip via coercion.

    def test_k_bool_rejected(self):
        p = base_payload()
        p["k"] = False
        self.assert_rejected_not_crash(p)
        # WHY: bool-as-int (0/1) can silently violate “k must be positive integer”.

    # -------------------------
    # existential typing issues
    # -------------------------

    def test_existential_none_rejected(self):
        p = base_payload()
        p["existential"] = None
        self.assert_rejected_not_crash(p)
        # WHY: Mode flags should be strictly boolean; None hides logic branches.

    def test_existential_string_rejected(self):
        p = base_payload()
        p["existential"] = "true"
        self.assert_rejected_not_crash(p)
        # WHY: String booleans are a common API input bug; don’t accept silently.

    def test_existential_int_rejected(self):
        p = base_payload()
        p["existential"] = 1
        self.assert_rejected_not_crash(p)
        # WHY: ints coercing to bool can mask upstream schema errors.

    # -------------------------
    # prune_masks typing issues
    # -------------------------

    def test_prune_masks_none_rejected(self):
        p = base_payload()
        p["prune_masks"] = None
        self.assert_rejected_not_crash(p)
        # WHY: List fields must not accept None; later loops expect iterables.

    def test_prune_masks_string_instead_of_list_rejected(self):
        p = base_payload()
        p["prune_masks"] = "0b0001"
        self.assert_rejected_not_crash(p)
        # WHY: Strings are iterable; treating them as a list causes per-char validation.

    def test_prune_masks_list_with_none_item_rejected(self):
        p = base_payload()
        p["prune_masks"] = [None]
        self.assert_rejected_not_crash(p)
        # WHY: None items would crash validate_bitstring (.startswith).

    def test_prune_masks_list_with_int_item_rejected(self):
        p = base_payload()
        p["prune_masks"] = [123]
        self.assert_rejected_not_crash(p)
        # WHY: Non-string items must not reach .startswith/int(...,0).

    def test_prune_masks_list_with_bytes_item_rejected(self):
        p = base_payload()
        p["prune_masks"] = [b"0b0001"]
        self.assert_rejected_not_crash(p)
        # WHY: bytes can pass some operations but break strict string constraints.

    # -------------------------
    # find_masks typing issues
    # -------------------------

    def test_find_masks_none_rejected(self):
        p = base_payload()
        p["find_masks"] = None
        self.assert_rejected_not_crash(p)
        # WHY: Prevents TypeErrors during list concatenation and iteration.

    def test_find_masks_tuple_instead_of_list_rejected(self):
        p = base_payload()
        p["find_masks"] = ("0b0001",)
        self.assert_rejected_not_crash(p)
        # WHY: Container type mismatches should fail early for consistent API contracts.

    def test_find_masks_list_with_dict_item_rejected(self):
        p = base_payload()
        p["find_masks"] = [{"mask": "0b0001"}]
        self.assert_rejected_not_crash(p)
        # WHY: Dicts are truthy/iterable; must not flow into string validators.

    # -------------------------
    # ranges typing issues
    # -------------------------

    def test_ranges_none_rejected(self):
        p = base_payload()
        p["ranges"] = None
        self.assert_rejected_not_crash(p)
        # WHY: Model validators and loops assume a list; None causes crashes.

    def test_ranges_string_instead_of_list_rejected(self):
        p = base_payload()
        p["ranges"] = "0b0000,0b0001"
        self.assert_rejected_not_crash(p)
        # WHY: Strings would be iterated as characters and explode during unpacking.

    def test_ranges_list_of_strings_rejected(self):
        p = base_payload()
        p["ranges"] = ["0b0000", "0b0001"]
        self.assert_rejected_not_crash(p)
        # WHY: Each range must be a 2-tuple; otherwise unpacking breaks.

    def test_ranges_singleton_tuple_rejected(self):
        p = base_payload()
        p["ranges"] = [("0b0000",)]
        self.assert_rejected_not_crash(p)
        # WHY: Wrong arity should validate cleanly, not crash on unpack.

    def test_ranges_triple_tuple_rejected(self):
        p = base_payload()
        p["ranges"] = [("0b0000", "0b0001", "0b0010")]
        self.assert_rejected_not_crash(p)
        # WHY: Extra elements must not be ignored or misinterpreted.

    def test_ranges_tuple_with_none_endpoint_rejected(self):
        p = base_payload()
        p["ranges"] = [(None, "0b0001")]
        self.assert_rejected_not_crash(p)
        # WHY: None endpoint would crash validate_bitstring and int conversion.

    def test_ranges_tuple_with_int_endpoint_rejected(self):
        p = base_payload()
        p["ranges"] = [(0, 1)]
        self.assert_rejected_not_crash(p)
        # WHY: Non-string endpoints must not reach int(...,0) parsing.

    def test_ranges_list_of_lists_rejected(self):
        p = base_payload()
        p["ranges"] = [["0b0000", "0b0001"]]
        self.assert_rejected_not_crash(p)
        # WHY: The declared type is Tuple[str,str]; list-vs-tuple mismatches
        # should fail.

    def test_ranges_nested_wrong_types_rejected(self):
        p = base_payload()
        p["ranges"] = [({"s": "0b0000"}, ["0b0001"])]
        self.assert_rejected_not_crash(p)
        # WHY: Mixed container types are common API bugs; must fail predictably.


if __name__ == "__main__":
    unittest.main()
