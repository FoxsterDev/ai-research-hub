"""Exact statistical bounds for suite aggregation (design P2.4).

Pure-stdlib implementations of the design's default decision-rule
primitives: one-sided Clopper-Pearson exact binomial bounds and the
distribution-free order-statistic lower confidence bound for a median.
The implementation is content-hashed so a suite or experiment can pin the
exact bound code it was decided with.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

METHOD_ID = "xuunity.stats.v1"

_BISECTION_ITERATIONS = 200


class StatsError(ValueError):
    pass


def implementation_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _require_counts(successes: int, trials: int) -> None:
    if trials <= 0:
        raise StatsError("trials must be positive")
    if not 0 <= successes <= trials:
        raise StatsError("successes must be within [0, trials]")


def _require_confidence(confidence: float) -> float:
    if not 0.5 < confidence < 1.0:
        raise StatsError("confidence must be in (0.5, 1.0)")
    return 1.0 - confidence


def binomial_cdf(successes: int, trials: int, probability: float) -> float:
    if probability <= 0.0:
        return 1.0
    if probability >= 1.0:
        return 0.0 if successes < trials else 1.0
    total = 0.0
    for count in range(successes + 1):
        total += (
            math.comb(trials, count)
            * probability**count
            * (1.0 - probability) ** (trials - count)
        )
    return min(total, 1.0)


def clopper_pearson_lower(
    successes: int, trials: int, confidence: float
) -> float:
    """One-sided exact lower bound for a binomial proportion."""
    _require_counts(successes, trials)
    alpha = _require_confidence(confidence)
    if successes == 0:
        return 0.0
    low, high = 0.0, 1.0
    for _ in range(_BISECTION_ITERATIONS):
        mid = (low + high) / 2.0
        tail = 1.0 - binomial_cdf(successes - 1, trials, mid)
        if tail > alpha:
            high = mid
        else:
            low = mid
    return low


def clopper_pearson_upper(
    successes: int, trials: int, confidence: float
) -> float:
    """One-sided exact upper bound for a binomial proportion."""
    _require_counts(successes, trials)
    alpha = _require_confidence(confidence)
    if successes == trials:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(_BISECTION_ITERATIONS):
        mid = (low + high) / 2.0
        tail = binomial_cdf(successes, trials, mid)
        if tail > alpha:
            low = mid
        else:
            high = mid
    return high


def median_lower_bound(
    values: list[float], confidence: float
) -> float | None:
    """Distribution-free one-sided lower confidence bound for the median.

    Returns the largest order statistic x_(k) such that
    P(Bin(n, 1/2) < k) <= 1 - confidence, or None when no order statistic
    achieves the requested confidence (sample too small)."""
    alpha = _require_confidence(confidence)
    ordered = sorted(values)
    trials = len(ordered)
    if trials == 0:
        return None
    best_index: int | None = None
    for index in range(1, trials + 1):
        if binomial_cdf(index - 1, trials, 0.5) <= alpha:
            best_index = index
        else:
            break
    if best_index is None:
        return None
    return ordered[best_index - 1]


def median(values: list[float]) -> float | None:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return None
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0
