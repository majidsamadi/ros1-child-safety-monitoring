from __future__ import annotations


def weighted_score(contact: float, wrap: float, lift: float, feet: float, struggle: float, comotion: float) -> float:
    return max(0.0, min(1.0,
        0.20 * contact +
        0.15 * wrap +
        0.25 * lift +
        0.15 * feet +
        0.15 * struggle +
        0.10 * comotion
    ))


def state_from_score(score: float) -> str:
    if score >= 0.75:
        return 'high_alert'
    if score >= 0.55:
        return 'warning'
    if score >= 0.25:
        return 'watch'
    return 'observing'
