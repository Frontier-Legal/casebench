"""Bootstrap intervals for a mean and for the difference between two paired runs (decision 0028)."""

import hashlib
from dataclasses import dataclass
from statistics import fmean

import numpy as np
from scipy.stats import bootstrap

# 95% is the convention the report states (decision 0028).
CONFIDENCE = 0.95


@dataclass(frozen=True)
class Interval:
    low: float
    high: float

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high


def seed(suite_id: str) -> int:
    """The same intervals on every machine for the same suite."""
    return int.from_bytes(hashlib.sha256(suite_id.encode()).digest()[:8], "big")


def _interval(data: tuple, statistic, suite_id: str, paired: bool) -> Interval:
    """No resampling where there is nothing to resample: one case, or every value the same.
    BCa needs variation; where it cannot compute, the percentile method is used instead."""
    arrays = [np.asarray(values, dtype=float) for values in data]
    point = float(statistic(*arrays))
    if len(arrays[0]) < 2 or all(np.ptp(values) == 0 for values in arrays):
        return Interval(point, point)
    for method in ("BCa", "percentile"):
        result = bootstrap(
            data,
            statistic,
            paired=paired,
            confidence_level=CONFIDENCE,
            method=method,
            rng=np.random.default_rng(seed(suite_id)),
        )
        low, high = result.confidence_interval
        if not (np.isnan(low) or np.isnan(high)):
            return Interval(float(low), float(high))
    return Interval(point, point)


def mean_interval(values: list[float], suite_id: str) -> Interval:
    return _interval((values,), np.mean, suite_id, paired=False)


def difference_interval(first: list[float], second: list[float], suite_id: str) -> Interval:
    """Paired case by case: the interval of mean(second) - mean(first)."""
    return _interval((first, second), lambda a, b: np.mean(b) - np.mean(a), suite_id, paired=True)


def mean(values: list[float]) -> float:
    return fmean(values) if values else 0.0
