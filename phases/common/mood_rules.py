"""Shared mood definitions for ranking and dataset tagging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from phases.common.config import PRODUCT_MOODS

DATASET_MOODS = ("ENERGISED", "FOCUSED", "LOW_KEY", "NOSTALGIC", "SAD")
AUDIO_FEATURES = ("energy", "valence", "tempo", "instrumentalness")


@dataclass(frozen=True)
class Threshold:
    check: Callable[[float], bool] | None
    active: bool = True

    @staticmethod
    def gt(value: float) -> "Threshold":
        return Threshold(check=lambda x: x > value)

    @staticmethod
    def lt(value: float) -> "Threshold":
        return Threshold(check=lambda x: x < value)

    @staticmethod
    def between(low: float, high: float) -> "Threshold":
        return Threshold(check=lambda x: low <= x <= high)

    @staticmethod
    def none() -> "Threshold":
        return Threshold(check=None, active=False)


MOOD_THRESHOLDS: dict[str, dict[str, Threshold]] = {
    "ENERGISED": {
        "energy": Threshold.gt(0.7),
        "valence": Threshold.gt(0.6),
        "tempo": Threshold.gt(120),
        "instrumentalness": Threshold.none(),
    },
    "FOCUSED": {
        "energy": Threshold.between(0.3, 0.6),
        "valence": Threshold.between(0.4, 0.6),
        "tempo": Threshold.between(80, 110),
        "instrumentalness": Threshold.gt(0.5),
    },
    "LOW_KEY": {
        "energy": Threshold.lt(0.4),
        "valence": Threshold.between(0.3, 0.6),
        "tempo": Threshold.lt(100),
        "instrumentalness": Threshold.none(),
    },
    "NOSTALGIC": {
        "energy": Threshold.between(0.3, 0.6),
        "valence": Threshold.between(0.4, 0.7),
        "tempo": Threshold.none(),
        "instrumentalness": Threshold.none(),
    },
    "SAD": {
        "energy": Threshold.lt(0.35),
        "valence": Threshold.lt(0.35),
        "tempo": Threshold.lt(100),
        "instrumentalness": Threshold.none(),
    },
}


MOOD_WEIGHT_VECTORS: dict[str, dict[str, float]] = {
    "ENERGISED": {"energy": 0.35, "valence": 0.25, "tempo": 0.30, "novelty": 0.10},
    "FOCUSED": {
        "energy": -0.20,
        "tempo": -0.15,
        "instrumentalness": 0.40,
        "novelty": 0.05,
    },
    "LOW_KEY": {"energy": -0.30, "valence": 0.10, "tempo": -0.25},
    "ADVENTUROUS": {
        "energy": 0.10,
        "valence": 0.05,
        "tempo": 0.10,
        "novelty": 0.45,
        "instrumentalness": 0.05,
    },
    "NOSTALGIC": {"energy": 0.10, "valence": 0.20, "tempo": 0.05},
    "SAD": {"energy": -0.35, "valence": -0.40, "tempo": -0.20},
}


def normalize_feature(name: str, value: float) -> float:
    if name == "tempo":
        return min(max(value / 200.0, 0.0), 1.0)
    return min(max(value, 0.0), 1.0)


def validate_product_mood(mood: str) -> str:
    value = mood.upper().strip()
    if value not in PRODUCT_MOODS:
        raise ValueError(f"Unsupported mood: {mood}")
    return value
