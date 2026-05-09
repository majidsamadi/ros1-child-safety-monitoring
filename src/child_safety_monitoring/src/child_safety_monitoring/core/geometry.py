from __future__ import annotations

from math import sqrt
from typing import Optional, Tuple

Point = Tuple[float, float]


def distance(a: Optional[Point], b: Optional[Point]) -> float:
    if a is None or b is None:
        return 1e9
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_inverse(value: float, low: float, high: float) -> float:
    if value <= low:
        return 1.0
    if value >= high:
        return 0.0
    return clamp01((high - value) / max(high - low, 1e-6))


def score_forward(value: float, low: float, high: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    return clamp01((value - low) / max(high - low, 1e-6))
